"""
scripts/check_env.py
Verifies environment is ready: Ollama running, model pulled, backend warm-up.
"""
import os
import sys
import time

def check_ollama():
    import ollama
    model = os.environ.get("MONEYMAP_MODEL", "gemma4:e4b")
    print(f"[check] Testing Ollama with model {model} ...")
    try:
        resp = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": "Say OK"}],
            options={"num_predict": 5, "temperature": 0},
        )
        print(f"  ✅ Ollama OK — response: {resp['message']['content'][:30]}")
        return True
    except Exception as e:
        print(f"  ❌ Ollama error: {e}")
        return False


def check_backend():
    import urllib.request
    url = "http://localhost:8000/api/health"
    try:
        with urllib.request.urlopen(url, timeout=3) as r:
            data = r.read().decode()
            print(f"  ✅ Backend OK — {data[:60]}")
            return True
    except Exception as e:
        print(f"  ❌ Backend not running: {e}")
        return False


def main():
    print("=" * 50)
    print("MoneyMap Environment Check")
    print("=" * 50)

    ok = True
    ok = check_ollama() and ok
    ok = check_backend() and ok

    print()
    if ok:
        print("✅ All systems ready!")
    else:
        print("❌ Some checks failed. See above.")
        sys.exit(1)


if __name__ == "__main__":
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    main()
