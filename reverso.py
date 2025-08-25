import subprocess
import json

def reverso_translate(text, source="english", target="french"):
    try:
        result = subprocess.run(
            ["node", "reverso_helper.js", text, source, target],
            capture_output=True,
            text=True,
            check=True
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print("Error:", e.stderr)
        return None

# Example usage
if __name__ == "__main__":
    res = reverso_translate("hello world", "english", "french")
    print(res)
