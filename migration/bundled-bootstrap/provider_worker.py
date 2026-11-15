"""One isolated, headless provider operation. Only the parent owns playback or download decisions."""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / 'resources/lib'))
import provider_fallback_worker
if __name__ == '__main__':
    provider_fallback_worker.main(sys.argv[1:])
