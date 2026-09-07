#!/usr/bin/env python3
import hashlib, json, os, pathlib, tarfile, urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1]
VERSION='0.160.0'
PINS={
 '0.147.0': ('17cc9a8f2e44e80ceff0e0647aec18b28a6b1b17823040e362ddc4a9fd017ccc','c0e263eeef8e4c176fac948b471b345bb177ff0fc929394391cd6c3143026b41'),
 '0.160.0': ('7bb60c584c241c86261c2b8697cd3725dd8c56691f5ad5d98454eaa005b47b0c','8524ac54f6e1d4d00d9ba5eea91daadec2ebc31e4da80db9c17eba2e859ecdd4'),
}

def setup(version=VERSION):
    sha,binary_sha=PINS[version]
    directory=ROOT/'.tools'; directory.mkdir(exist_ok=True); binary=directory/f'otelcol-contrib-{version}'
    if os.environ.get('OTELCOL'): binary=pathlib.Path(os.environ['OTELCOL']).resolve()
    if binary.exists():
        if hashlib.sha256(binary.read_bytes()).hexdigest()!=binary_sha: raise RuntimeError('cached collector binary checksum mismatch')
        return binary
    archive=directory/f'collector-{version}.tar.gz'
    urllib.request.urlretrieve(f'https://github.com/open-telemetry/opentelemetry-collector-releases/releases/download/v{version}/otelcol-contrib_{version}_linux_amd64.tar.gz',archive)
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=sha: raise RuntimeError('collector archive checksum mismatch')
    with tarfile.open(archive) as tar:
        member=next(m for m in tar.getmembers() if pathlib.PurePosixPath(m.name).name=='otelcol-contrib')
        with tar.extractfile(member) as source: binary.write_bytes(source.read())
    binary.chmod(0o755); archive.unlink()
    if hashlib.sha256(binary.read_bytes()).hexdigest()!=binary_sha: raise RuntimeError('collector binary checksum mismatch')
    return binary

if __name__=='__main__': print(setup())
