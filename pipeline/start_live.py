"""Start the free station API without a historical DB or TensorFlow.
Paste the OpenAQ API key at a hidden prompt; it is passed only to the child
process environment and never written to disk or shown in the frontend.
"""
import getpass
import os
import pathlib
import subprocess

if __name__ == '__main__':
    env = os.environ.copy()
    key = env.get('OPENAQ_API_KEY') or getpass.getpass('OpenAQ API key (hidden): ').strip()
    if not key:
        raise SystemExit('A private OpenAQ API key is required. No fake readings will be shown.')
    env.update(OPENAQ_API_KEY=key, LIVE_ONLY='true')
    env.setdefault('CORS_ALLOW_ORIGIN', 'http://localhost:3000')
    raise SystemExit(subprocess.call(['go', 'run', '.'], cwd=pathlib.Path(__file__).resolve().parents[1], env=env))
