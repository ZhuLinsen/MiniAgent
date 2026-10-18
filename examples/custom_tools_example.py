"""A read-only native tool and owned cleanup. This calls a real provider."""
import argparse
from miniagent import Harness, Plugin, Policy, Tool
from miniagent.config import load_config


def calculator(ctx):
    ctx.tool(Tool("add_one", "Add one to an integer", {
        "type": "object", "properties": {"n": {"type": "integer"}}, "required": ["n"]},
        lambda n, path: n + 1, access="read"))
    ctx.cleanup(lambda: print("Calculator plugin closed"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", help="provider:model-id")
    args = parser.parse_args()
    cfg = load_config(model_override=args.model)
    app = Harness(model=cfg.llm.model, providers=cfg.providers, api_key=cfg.llm.api_key,
                  base_url=cfg.llm.api_base, temperature=cfg.llm.temperature,
                  policy=Policy(mode="readonly"))
    app.use(Plugin("calculator", calculator))
    print(app.run("Use add_one with n=2, then report its result."))


if __name__ == "__main__":
    main()
