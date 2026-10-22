"""Restore omitted model weights at the pinned revisions; verify every SHA-256."""
from pathlib import Path
import hashlib,json,urllib.request

root=Path(__file__).resolve().parent/'models'
for folder in ['embedding','qa']:
    base=root/folder
    manifest=json.loads((base/'model-manifest.json').read_text(encoding='utf-8'))
    for item in manifest['files']:
        path=base/item['path']
        if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256']:continue
        tail=f"/{manifest['repo']}/resolve/{manifest['revision']}/{item['path']}?download=true"
        error=None
        for host in ['https://hf-mirror.com','https://huggingface.co']:
            try:
                with urllib.request.urlopen(host+tail,timeout=60) as response:data=response.read()
                if hashlib.sha256(data).hexdigest()!=item['sha256']:raise ValueError('Downloaded model hash mismatch')
                path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);error=None;break
            except Exception as e:error=e
        if error:raise error
        print('Verified',folder,item['path'],flush=True)
print('Pinned model files are ready.')
