"""Run: python examples/quickstart.py"""
from dust import Layer
from dust.backends import Scripted

layer = Layer()

# 1. Check text
for text in ["Christ is risen.", "Jesus was a created being.", "Arius taught that the Son was created."]:
    v = layer.check(text)
    print(f"{v.decision:5s} {text}")
    for x in v.violations:
        print("      ", x.proof[-1])

# 2. Wrap a model. Swap Scripted for OpenAICompatible("http://localhost:11434/v1", "qwen2.5:3b-instruct").
model = layer.wrap(Scripted(["The Son is a creature.", "The Son is begotten, not made, of one substance with the Father."]))
r = model.chat([{"role": "user", "content": "Is the Son a creature?"}])
print("\nanswer:", r.content, f"(attempts={r.attempts}, repaired={r.repaired})")
