"""Command line: dust check | refs | audit | creed | prompt | modelfile | serve"""
from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="dust", description="Nicene (381) alignment layer for open models")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check", help="check text (argument or stdin)")
    c.add_argument("text", nargs="?")
    c.add_argument("--mode", default="dual", choices=["dual", "symbolic", "neural"])
    c.add_argument("--json", action="store_true")
    c.add_argument("--extension", action="append", default=[], help="stack a confession extension, e.g. chalcedon-451")
    c.add_argument("--bible", help="verses.jsonl for quotation checks (web-bible-rag format)")
    rf = sub.add_parser("refs", help="list Bible references in text and whether they exist")
    rf.add_argument("text", nargs="?")
    cr = sub.add_parser("creed", help="print the Creed")
    cr.add_argument("--lang", default="en", choices=["en", "grc", "la"])
    p = sub.add_parser("prompt", help="print the system prompt, optionally grounded on a question")
    p.add_argument("query", nargs="?")
    au = sub.add_parser("audit", help="audit the encoded boundary: consistency, coverage, fingerprint")
    au.add_argument("--extension", action="append", default=[])
    au.add_argument("--json", action="store_true")
    mf = sub.add_parser("modelfile", help="print an Ollama Modelfile carrying the constitution and Creed (prompt layer only)")
    mf.add_argument("--base", default="qwen2.5:3b-instruct", help="Ollama base model")
    s = sub.add_parser("serve", help="run the HTTP API")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8381)
    s.add_argument("--backend", help="OpenAI-compatible base URL, e.g. http://localhost:11434/v1")
    s.add_argument("--model", default="", help="model name at the backend")
    args = ap.parse_args(argv)

    from .layer import Layer
    if args.cmd == "creed":
        from .kb import load
        print(load().creed_text(args.lang))
        return 0
    if args.cmd == "prompt":
        print(Layer(mode="symbolic").system_prompt(args.query))
        return 0
    if args.cmd == "modelfile":
        from .audit import fingerprint
        lay = Layer(mode="symbolic")
        prompt = lay.system_prompt().replace('"""', "'''")
        print(f"# Dust prompt-layer model on {args.base}. Boundary fingerprint {fingerprint(lay.kb)[:16]}.")
        print("# This carries the constitution and the Creed only. It does NOT run the checker or the")
        print("# repair loop: for those, put `dust serve --backend http://localhost:11434/v1` in front of it.")
        print("# Build:  ollama create dust-<tier> -f Modelfile")
        print(f"FROM {args.base}")
        print("PARAMETER temperature 0.3")
        print('SYSTEM """' + prompt + '"""')
        return 0
    if args.cmd == "audit":
        from .audit import audit
        from .kb import load
        rep = audit(load(tuple(args.extension)))
        if args.json:
            print(json.dumps(rep.to_dict(), indent=1, ensure_ascii=False))
        else:
            print(("OK" if rep.ok else "PROBLEMS") + f"  boundary fingerprint {rep.fingerprint[:16]}")
            for k, v in rep.stats.items():
                print(f"  {k}: {v}")
            for p_ in rep.problems:
                print(f"  PROBLEM {p_}")
            for w in rep.warnings:
                print(f"  note    {w}")
        return 0 if rep.ok else 1
    if args.cmd == "refs":
        from .scripture import find
        text = args.text if args.text is not None else sys.stdin.read()
        refs = find(text)
        for r in refs:
            print(f"{r.canonical}\t{'ok' if r.exists else 'INVALID: ' + r.problem}")
        return 0 if all(r.exists for r in refs) else 1
    if args.cmd == "check":
        text = args.text if args.text is not None else sys.stdin.read()
        bible = None
        if args.bible:
            from .scripture import Bible
            bible = Bible.from_jsonl(args.bible)
        v = Layer(mode=args.mode, extensions=args.extension, bible=bible).check(text)
        if args.json:
            print(json.dumps(v.to_dict(), indent=1, ensure_ascii=False))
        else:
            print(v.decision.upper())
            for x in v.violations + v.flags:
                kind = "BLOCK" if x in v.violations else "FLAG"
                print(f"  {kind} {x.proposition} via {x.source} ({x.confidence:.2f}): {x.sentence}")
                for step in x.proof:
                    print(f"      {step}")
            for r in v.references:
                status = "ok" if r["exists"] else f"DOES NOT EXIST ({r['problem']})"
                q = f", quote similarity {r['quote_similarity']}" if r.get("quote_similarity") is not None else ""
                print(f"  REF {r['canonical']}: {status}{q}")
        return 0 if v.decision != "block" else 1
    if args.cmd == "serve":
        from .server import serve
        backend = None
        if args.backend:
            from .backends import OpenAICompatible
            backend = OpenAICompatible(args.backend, args.model)
        httpd = serve(Layer(), args.host, args.port, backend, args.model or "dust")
        print(f"dust listening on http://{args.host}:{args.port}  (open it in a browser for Dust Study)", file=sys.stderr)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
