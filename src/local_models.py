"""Offline ONNX encoders and sliding-window extractive QA; never read annotations."""
from pathlib import Path
import hashlib
import json


def _runtime(folder, max_length, stride=0):
    import onnxruntime as ort
    from tokenizers import Tokenizer
    folder = Path(folder)
    tokenizer = Tokenizer.from_file(str(folder / 'tokenizer.json'))
    tokenizer.enable_truncation(max_length=max_length, stride=stride,
                                strategy='only_second' if stride else 'longest_first')
    tokenizer.enable_padding(pad_id=tokenizer.token_to_id('[PAD]') or 0, pad_token='[PAD]')
    options = ort.SessionOptions()
    options.intra_op_num_threads = 4
    options.inter_op_num_threads = 1
    session = ort.InferenceSession(str(folder / 'onnx/model_quantized.onnx'),
                                   sess_options=options, providers=['CPUExecutionProvider'])
    return tokenizer, session


def _inputs(session, encodings):
    import numpy as np
    values = {'input_ids': [e.ids for e in encodings],
              'attention_mask': [e.attention_mask for e in encodings],
              'token_type_ids': [e.type_ids for e in encodings]}
    return {item.name: np.asarray(values[item.name], dtype=np.int64) for item in session.get_inputs()}


class OnnxEncoder:
    def __init__(self, folder):
        self.tokenizer, self.session = _runtime(folder, 128)
        self.cache = {}

    def encode(self, texts):
        import numpy as np
        outputs = []
        for offset in range(0, len(texts), 32):
            encodings = self.tokenizer.encode_batch(texts[offset:offset+32])
            inputs = _inputs(self.session, encodings)
            hidden = self.session.run(None, inputs)[0]
            mask = inputs['attention_mask'][..., None]
            pooled = (hidden * mask).sum(axis=1) / mask.sum(axis=1).clip(min=1)
            pooled /= np.linalg.norm(pooled, axis=1, keepdims=True).clip(min=1e-12)
            outputs.append(pooled.astype(np.float32))
        return np.concatenate(outputs) if outputs else np.zeros((0, 384), dtype=np.float32)

    def scores(self, question, memories):
        key = hashlib.sha256(json.dumps([m['memory_id'] for m in memories]).encode()).hexdigest()
        if key not in self.cache:
            self.cache[key] = self.encode([m['entity'] + ': ' + m['content'] for m in memories])
        q = self.encode([question])[0]
        return [float(v @ q) for v in self.cache[key]]


class OnnxAnswerer:
    """SQuAD v1 span model. Every context token is covered by overlapping windows."""
    def __init__(self, folder):
        self.tokenizer, self.session = _runtime(folder, 384, stride=96)
        self.model_id = 'Xenova/distilbert-base-cased-distilled-squad:int8'

    def answer(self, question, context):
        import numpy as np
        if not context.strip():
            return {'answer': 'Insufficient evidence.', 'windows': 0, 'covered_context_tokens': 0}
        encoding = self.tokenizer.encode(question, context)
        windows = [encoding] + encoding.overflowing
        best = None
        covered = set()
        for offset in range(0, len(windows), 8):
            chunk = windows[offset:offset+8]
            # Overflow encodings may have different lengths: pad a copy of the numerical input.
            max_len = max(len(e.ids) for e in chunk)
            batch = {}
            for item in self.session.get_inputs():
                field = {'input_ids': 'ids', 'attention_mask': 'attention_mask', 'token_type_ids': 'type_ids'}[item.name]
                batch[item.name] = np.asarray([getattr(e, field) + [0]*(max_len-len(e.ids)) for e in chunk], dtype=np.int64)
            starts, ends = self.session.run(None, batch)[:2]
            for row, encoded in enumerate(chunk):
                valid = [i for i, seq in enumerate(encoded.sequence_ids) if seq == 1 and encoded.attention_mask[i] and encoded.offsets[i][1] > encoded.offsets[i][0]]
                covered.update(encoded.offsets[i] for i in valid)
                if not valid: continue
                # Softmax within context tokens, then compare span likelihoods across windows.
                s, e = starts[row, valid], ends[row, valid]
                s = s - np.logaddexp.reduce(s); e = e - np.logaddexp.reduce(e)
                svalues, evalues = dict(zip(valid, s)), dict(zip(valid, e))
                for start in sorted(valid, key=lambda i: -svalues[i])[:20]:
                    for end in sorted(valid, key=lambda i: -evalues[i])[:20]:
                        if start <= end < start + 30:
                            score = float(svalues[start] + evalues[end])
                            a, b = encoded.offsets[start][0], encoded.offsets[end][1]
                            candidate = (score, -a, a, b)
                            if best is None or candidate > best: best = candidate
        if best is None:
            return {'answer': 'Insufficient evidence.', 'windows': len(windows), 'covered_context_tokens': len(covered)}
        return {'answer': context[best[2]:best[3]], 'windows': len(windows),
                'covered_context_tokens': len(covered), 'span_start': best[2], 'span_end': best[3],
                'span_log_probability': best[0], 'model_id': self.model_id,
                'coverage_policy': 'all context windows; no Top-K window selection'}
