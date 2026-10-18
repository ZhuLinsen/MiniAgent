"""Configured model, coding tools and durable session. This calls a real provider."""
import argparse
from miniagent import Harness, Policy, Session
from miniagent.config import load_config
from miniagent.plugins import coding_tools


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", help="provider:model-id")
    parser.add_argument("prompt")
    parser.add_argument("--session", required=True)
    args = parser.parse_args()
    cfg = load_config(model_override=args.model)
    app = Harness(model=cfg.llm.model, providers=cfg.providers, api_key=cfg.llm.api_key,
                  base_url=cfg.llm.api_base, temperature=cfg.llm.temperature,
                  policy=Policy(mode="readonly"))
    app.session = Session(args.session)
    app.use(coding_tools())
    print(app.run(args.prompt))


if __name__ == "__main__":
    main()
