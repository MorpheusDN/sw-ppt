"""Offline, evidence-preserving requirements-engineering prototype. Python 3.10+."""
from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta

VERSION = "0.5.1-locomo-onnx"
STOP = set("a an the is are was were i my me you your he she it we they to of in on at for and or do does did what where when how now current currently status as before after has have had s".split())
STAGES = {"researching": 1, "applied": 2, "interviews_passed": 3, "adopted": 4}


def parse_time(value):
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise ValueError("Time must be a string or null")
    value = value.strip()
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        # All times are naive corpus-local. Do not silently strip timezone offsets.
        if dt.tzinfo:
            raise ValueError("Use corpus-local time without a timezone offset")
        return dt.isoformat(timespec="seconds")
    except ValueError:
        pass
    for fmt in ("%I:%M %p on %d %B, %Y", "%H:%M on %d %B, %Y", "%d %B %Y", "%d %b %Y"):
        try:
            return datetime.strptime(value, fmt).isoformat(timespec="seconds")
        except ValueError:
            continue
    raise ValueError(f"Unrecognized corpus-local timestamp: {value}")


def event_time(text, session_time):
    explicit = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", text)
    if explicit:
        return parse_time(explicit[1]), explicit[1], "event"
    relative = re.search(r"\b(last (?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)|yesterday|today|last week|last month|next week|tomorrow|\d+ years? ago)\b", text, re.I)
    if relative:
        expr = relative[0].lower()
        if not session_time:
            return None, expr, "unknown"
        base = datetime.fromisoformat(session_time)
        if expr in ("yesterday", "today"):
            base -= timedelta(days=1 if expr == "yesterday" else 0)
            return base.replace(hour=0, minute=0, second=0).isoformat(), expr, "event"
        weekdays = "monday tuesday wednesday thursday friday saturday sunday".split()
        if expr.startswith("last ") and expr[5:] in weekdays:
            delta = (base.weekday() - weekdays.index(expr[5:])) % 7 or 7
            base = (base - timedelta(days=delta)).replace(hour=0, minute=0, second=0)
            return base.isoformat(), expr, "event"
        return None, expr, "unknown"
    # Other temporal wording is not silently interpreted as the session date.
    if re.search(r"\b(ago|previous|earlier|later|next|last|in 20\d\d)\b", text, re.I):
        return None, "unresolved temporal expression", "unknown"
    return session_time, None, "utterance" if session_time else "unknown"


def normalize_dataset(raw):
    """Read raw conversation fields only. Never consume QA/observations/summaries."""
    records = raw.get("conversations", []) if isinstance(raw, dict) else raw
    if not isinstance(records, list) or not records:
        raise ValueError("Expected a non-empty list or {conversations: [...]}")
    result, ids = [], set()
    for sample in records:
        if not isinstance(sample, dict):
            raise ValueError("Each conversation must be an object")
        cid = sample.get("conversation_id", sample.get("sample_id"))
        if not isinstance(cid, str) or not cid or cid in ids:
            raise ValueError("Conversation IDs must be non-empty unique strings")
        ids.add(cid)
        if "conversation" in sample:
            conv = sample["conversation"]
            if not isinstance(conv, dict):
                raise ValueError("LoCoMo conversation must be an object")
            keys = sorted((k for k in conv if re.fullmatch(r"session_\d+", k)), key=lambda k: int(k.split("_")[-1]))
            if any(not isinstance(conv[k], list) or any(not isinstance(t, dict) for t in conv[k]) for k in keys):
                raise ValueError("LoCoMo sessions must contain lists of turn objects")
            sessions = [{"session_id": int(k.split("_")[-1]), "timestamp": conv.get(k + "_date_time"),
                         "turns": [{"turn_id": t.get("dia_id"), "speaker": t.get("speaker"), "text": t.get("text")} for t in conv[k]]} for k in keys]
        else:
            sessions = sample.get("sessions", [])
        if not isinstance(sessions, list) or not sessions:
            raise ValueError(f"No sessions in {cid}")
        normalized, turns_seen, sessions_seen = [], set(), set()
        for session in sessions:
            if not isinstance(session, dict):
                raise ValueError("Each session must be an object")
            sid = session.get("session_id")
            if isinstance(sid, bool) or not isinstance(sid, (int, str)) or str(sid) in sessions_seen:
                raise ValueError("Session IDs must be present and unique within conversation")
            sessions_seen.add(str(sid))
            timestamp = parse_time(session.get("timestamp"))
            turns = session.get("turns")
            if not isinstance(turns, list):
                raise ValueError("turns must be a list")
            clean_turns = []
            for turn in turns:
                if not isinstance(turn, dict):
                    raise ValueError("Each turn must be an object")
                if any(not isinstance(turn.get(k), str) or not turn[k].strip() for k in ("turn_id", "speaker", "text")):
                    raise ValueError("Each turn needs turn_id, speaker and non-empty text")
                if turn["turn_id"] in turns_seen:
                    raise ValueError(f"Duplicate turn {cid}/{turn['turn_id']}")
                turns_seen.add(turn["turn_id"])
                clean_turns.append({k: turn[k] for k in ("turn_id", "speaker", "text")})
            normalized.append({"session_id": sid, "timestamp": timestamp, "turns": clean_turns})
        result.append({"conversation_id": cid, "sessions": normalized})
    return result


def extract(conversations):
    memories = []
    for conv in conversations:
        for session in conv["sessions"]:
            for turn in session["turns"]:
                # Sentence boundaries, not arbitrary character windows, preserve evidence.
                sentences = re.split(r"(?<=[.!?])\s+", turn["text"])
                for index, content in enumerate(sentences):
                    content = content.strip()
                    if not content:
                        continue
                    attr, value, entity = "observation", content, turn["speaker"]
                    low = content.lower()
                    # Structured facts require an explicit first-person subject.
                    self_assertion = bool(re.search(r"\b(i|my|i've|i’m|i'm)\b", low))
                    modality = "plan" if re.search(r"\b(will|plan to|planning to|hope to|want to|might|may)\b", low) else "assertion"
                    if self_assertion:
                        if re.search(r"\b(i(?:'ve| have)? (?:just )?(?:passed .*adoption|passed the adoption))", low):
                            attr, value = "adoption_status", "interviews_passed"
                        elif re.search(r"\bi (?:have )?applied (?:to|for).*adoption", low):
                            attr, value = "adoption_status", "applied"
                        elif re.search(r"\bi(?:'m| am| have been)? research(?:ing|ed).*adoption", low):
                            attr, value = "adoption_status", "researching"
                        elif re.search(r"\bi (?:have )?adopted\b", low):
                            attr, value = "adoption_status", "adopted"
                        else:
                            for pattern, attribute in [
                                (r"\bi (?:now )?(?:live in|moved to) ([A-Za-z][A-Za-z -]*?)(?:[.!?,]|$| since | on )", "residence"),
                                (r"\bi (?:still )?work at ([A-Za-z][A-Za-z -]*?)(?:[.!?,]|$| since | on )", "employment"),
                                (r"\bi lost my job at ([A-Za-z][A-Za-z -]*?)(?:[.!?,]|$| on | last | yesterday)", "employment_left"),
                                (r"\bi (?:enjoy|like|love) ([A-Za-z][A-Za-z -]*?)(?:[.!?,]|$)", "hobby")]:
                                match = re.search(pattern, content, re.I)
                                if match:
                                    attr, value = attribute, match[1].strip()
                                    if attr.startswith("employment"):
                                        attr, value = "employment:" + value.casefold(), "left" if attr.endswith("_left") else "working"
                                    break
                    # Elliptical self reports and pet ownership remain distinct from child adoption.
                    if attr == "observation" and re.match(r"^researching adoption agencies\b", low):
                        attr, value = "adoption_status", "researching"
                    if attr == "observation":
                        if re.search(r"\bno pets (?:right )?now\b", low):
                            attr, value = "pet_ownership", "none"
                        elif re.search(r"\b(?:i|we) (?:recently |just )?(?:adopted|got) (?:another |a |this )?(?:cute )?(?:pup|puppy|dog)\b|\bmy puppy\b|\bhaving two dogs\b", low):
                            attr, value = "pet_ownership", "owns_dog"
                    et, expr, basis = event_time(content, session["timestamp"])
                    mid = "mem_" + hashlib.sha256(f"{conv['conversation_id']}\0{turn['turn_id']}\0{index}".encode()).hexdigest()[:20]
                    memories.append({"memory_id": mid, "conversation_id": conv["conversation_id"], "content": content,
                                     "entity": entity, "attribute": attr, "value": value,
                                     "session_time": session["timestamp"], "event_time": et,
                                     "time_expression": expr, "time_basis": basis, "modality": modality,
                                     "extraction_method": "rules-v1" if attr != "observation" else "verbatim-fallback",
                                     "source": {"session": session["session_id"], "turns": [turn["turn_id"]], "text": turn["text"]}})
    return memories


def tokens(text):
    return [t for t in re.findall(r"[a-z0-9]+", text.casefold()) if t not in STOP]


def lexical_scores(question, memories):
    # TF-IDF cosine is named honestly: it is not Sentence-BERT or Full Text.
    documents = [Counter(tokens(m["entity"] + " " + m["content"] + " " + m["attribute"])) for m in memories]
    df = Counter(t for doc in documents for t in doc)
    idf = {t: math.log((1 + len(documents)) / (1 + n)) + 1 for t, n in df.items()}
    def vector(counter):
        v = {t: n * idf.get(t, 1) for t, n in counter.items()}
        norm = math.sqrt(sum(n*n for n in v.values())) or 1
        return {t: n/norm for t, n in v.items()}
    q = vector(Counter(tokens(question)))
    return [sum(q.get(t, 0)*n for t, n in vector(d).items()) for d in documents]


class DenseRetriever:
    def __init__(self, model_path):
        if not model_path:
            raise ValueError("Vector methods require a local SentenceTransformer model path")
        from pathlib import Path
        self.onnx = None
        if (Path(model_path) / 'onnx/model_quantized.onnx').is_file():
            from local_models import OnnxEncoder
            self.onnx = OnnxEncoder(model_path)
            return
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            raise ValueError("Install requirements-vector.txt and provide a local model. No lexical substitution is allowed.") from e
        self.model = SentenceTransformer(model_path, local_files_only=True)
        self.cache = {}

    def scores(self, question, memories):
        if self.onnx is not None:
            return self.onnx.scores(question, memories)
        key = hashlib.sha256(json.dumps(memories, sort_keys=True).encode()).hexdigest()
        if key not in self.cache:
            self.cache[key] = self.model.encode([m["entity"] + ": " + m["content"] for m in memories], normalize_embeddings=True)
        q = self.model.encode([question], normalize_embeddings=True)[0]
        return [float(v @ q) for v in self.cache[key]]


def query_scope(question, memories, entity=None, attribute=None):
    names = sorted(set(m["entity"] for m in memories), key=len, reverse=True)
    matches = [name for name in names if re.search(r"\b" + re.escape(name) + r"\b", question, re.I)]
    if entity is None and len(matches) == 1:
        entity = matches[0]
    if entity is None and len(matches) > 1:
        raise ValueError("Multiple entities: select a target entity or split the question")
    if entity is not None and entity not in names:
        raise ValueError("Unknown entity")
    low = question.lower()
    if attribute is None:
        if "adopt" in low:
            attribute = "adoption_status"
        elif any(x in low for x in ("live", "living", "residence", "moved")):
            attribute = "residence"
        elif any(x in low for x in ("hobby", "hobbies", "enjoy")):
            attribute = "hobby"
        elif "work" in low or "job" in low:
            companies = [m["attribute"] for m in memories if m["attribute"].startswith("employment:") and m["attribute"].split(":", 1)[1] in low]
            if companies:
                attribute = sorted(set(companies))[0]
    return entity, attribute


def relation(old, new):
    """Pair semantics. RETAIN also covers independent attributes or events."""
    if (old["conversation_id"], old["entity"], old["attribute"]) != (new["conversation_id"], new["entity"], new["attribute"]):
        return "RETAIN", "different entity or attribute"
    if old["attribute"] in ("observation", "hobby") or old["modality"] != "assertion" or new["modality"] != "assertion":
        return "RETAIN", "independent observation, set-valued attribute, or plan"
    if str(old["value"]).casefold() == str(new["value"]).casefold():
        return "RETAIN", "consistent repeated evidence"
    t1, t2 = old["event_time"], new["event_time"]
    if not t1 or not t2 or t1 == t2:
        return "CONFLICT", "different scalar values without a reliable temporal order"
    if t1 > t2:
        old, new = new, old
    if old["attribute"] == "adoption_status":
        if STAGES.get(new["value"], 0) > STAGES.get(old["value"], 0):
            return "UPDATE", "later explicit stage in the same process"
        return "CONFLICT", "unsupported process regression"
    return "SUPERSEDE", "later assertion of the same scalar attribute"


def resolve(memories, as_of):
    decisions, eligible, relations = {}, [], []
    for m in memories:
        reason = None
        if m["modality"] != "assertion":
            reason = "UNCERTAIN_PLAN"
        elif as_of and m["event_time"] and m["event_time"] > as_of:
            reason = "FUTURE"
        elif not m["event_time"]:
            reason = "UNCERTAIN_TIME"
        if reason:
            decisions[m["memory_id"]] = reason
        else:
            decisions[m["memory_id"]] = "EFFECTIVE"
            eligible.append(m)
    # Unknown-time facts may conflict with dated facts. Never silently pick the dated one.
    comparable = [m for m in memories if decisions[m["memory_id"]] not in ("FUTURE", "UNCERTAIN_PLAN")]
    groups = defaultdict(list)
    for m in comparable:
        groups[(m["entity"], m["attribute"])].append(m)
    for group in groups.values():
        def order_key(m):
            turn_numbers = tuple(int(v) for v in re.findall(r'\d+', m['source']['turns'][0]))
            return (m["event_time"] or "", turn_numbers, m["memory_id"])
        ordered = sorted(group, key=order_key)
        for i, old in enumerate(ordered):
            for new in ordered[i+1:]:
                label, reason = relation(old, new)
                relations.append({"from_id": old["memory_id"], "to_id": new["memory_id"], "label": label, "reason": reason})
                if label == "CONFLICT":
                    decisions[old["memory_id"]] = decisions[new["memory_id"]] = "CONFLICT"
                elif label in ("UPDATE", "SUPERSEDE") and decisions[old["memory_id"]] != "CONFLICT":
                    decisions[old["memory_id"]] = "HISTORICAL"
    effective = [m for m in eligible if decisions[m["memory_id"]] == "EFFECTIVE"]
    return effective, relations, decisions


class Engine:
    def __init__(self, raw, model_path=None):
        self.conversations = normalize_dataset(raw)
        self.memories = extract(self.conversations)
        self.dense = DenseRetriever(model_path) if model_path else None

    def query(self, conversation_id, question, k=10, as_of=None, entity=None, attribute=None, method="dynamic_lexical", open_domain=False):
        if not isinstance(question, str) or not question.strip():
            raise ValueError("question must be non-empty")
        if isinstance(k, bool) or not isinstance(k, int) or not 1 <= k <= 100:
            raise ValueError("k must be an integer from 1 to 100")
        if method not in ("dynamic_lexical", "lexical", "vector", "dynamic_vector", "hybrid", "full_text"):
            raise ValueError("Unknown method")
        conv = next((c for c in self.conversations if c["conversation_id"] == conversation_id), None)
        if conv is None:
            raise ValueError("Unknown conversation_id")
        all_mem = [m for m in self.memories if m["conversation_id"] == conversation_id]
        if not open_domain:
            entity, attribute = query_scope(question, all_mem, entity, attribute)
        explicit_as_of = as_of is not None
        if as_of is None:
            # Auto-understand unambiguous ISO dates only, otherwise require the time control.
            iso = re.search(r"\b20\d{2}-\d{2}-\d{2}\b", question)
            if iso:
                as_of = iso[0] + "T23:59:59"
                explicit_as_of = True
            elif not open_domain and re.search(r"\b(before|after|in 20\d\d|last (?:year|month|week))\b", question, re.I):
                raise ValueError("Historical question requires an explicit as_of timestamp")
        if as_of is not None:
            as_of = parse_time(as_of)
        else:
            as_of = max((s["timestamp"] for s in conv["sessions"] if s["timestamp"]), default=None)
        # All methods use identical, query-derived entity/attribute metadata constraints.
        pool = [m for m in all_mem if (entity is None or m["entity"] == entity) and (attribute is None or m["attribute"] == attribute)]
        if method in ("vector", "dynamic_vector", "hybrid") and self.dense is None:
            raise ValueError("Vector method unavailable: configure a local SentenceTransformer model")
        if method in ("vector", "dynamic_vector"):
            scores = self.dense.scores(question, pool) if pool else []
        else:
            scores = lexical_scores(question, pool)
            if method == "hybrid" and pool:
                dense = self.dense.scores(question, pool)
                # Reciprocal rank fusion avoids incomparable score scales.
                fused = [0.0]*len(pool)
                for s in (scores, dense):
                    for rank, i in enumerate(sorted(range(len(s)), key=lambda i: (-s[i], pool[i]["memory_id"])), 1):
                        fused[i] += 1/(60+rank)
                scores = fused
        ranked = sorted(zip(pool, scores), key=lambda item: (-item[1], item[0]["memory_id"]))
        # Known attribute is an explicit semantic constraint. General queries require lexical overlap.
        if attribute is None and method in ("dynamic_lexical", "lexical", "full_text"):
            ranked = [(m, s) for m, s in ranked if set(tokens(question)) & set(tokens(m["content"]))]
        candidates = [dict(m, retrieval_score=round(s, 6)) for m, s in ranked[:k]]
        if method in ("dynamic_lexical", "dynamic_vector", "hybrid"):
            effective, relations, decisions = resolve(candidates, as_of)
        else:
            effective, relations = candidates, []
            decisions = {m["memory_id"]: "RETRIEVED_UNRESOLVED" for m in candidates}
        uncertain = any(v in ("CONFLICT", "UNCERTAIN_TIME", "UNCERTAIN_PLAN") for v in decisions.values())
        if method.startswith("dynamic") or method == "hybrid":
            if uncertain:
                status, answer = "uncertain", "Cannot determine reliably from the available evidence."
            elif not effective:
                status, answer = "insufficient_evidence", "Insufficient evidence."
            else:
                status = "answered"
                answer = "; ".join(dict.fromkeys(str(m["value"]) for m in effective))
        else:
            status = "answered" if effective else "insufficient_evidence"
            answer = "; ".join(dict.fromkeys(str(m["value"]) for m in effective)) if effective else "Insufficient evidence."
        # Full Text context is complete raw history, with no Top-K truncation.
        full_context = "\n".join(f"[{s['timestamp']} {t['turn_id']}] {t['speaker']}: {t['text']}" for s in conv["sessions"] for t in s["turns"])
        context = full_context if method == "full_text" else "\n".join(f"[{','.join(m['source']['turns'])}] {m['entity']}: {m['content']}" for m in effective)
        if method == "full_text":
            # Offline extractive mode cannot fairly evaluate Full Text LLM reasoning.
            answer, status = "Full raw conversation prepared. Configure an answer model for this baseline.", "context_only"
        qid = "q_" + hashlib.sha256(json.dumps([conversation_id, question, k, as_of, entity, attribute, method]).encode()).hexdigest()[:16]
        return {"query_id": qid, "conversation_id": conversation_id, "question": question, "method": method,
                "as_of": as_of, "time_reference": "explicit" if explicit_as_of else "conversation_end",
                "scope": {"entity": entity, "attribute": attribute}, "candidates": candidates,
                "relations": relations, "decisions": decisions, "effective_ids": [m["memory_id"] for m in effective],
                "answer": answer, "answer_status": status, "evidence_ids": [m["memory_id"] for m in effective],
                "context": context, "answer_mode": "extractive-demo" if method != "full_text" else "context-only",
                "engine_version": VERSION, "warning": "Synthetic/local prototype results are not course benchmark results."}


def export_bundle(engine):
    return {"schema_version": "1.0", "engine_version": VERSION, "memories": engine.memories}
