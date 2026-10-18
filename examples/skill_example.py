"""Apply a native Skill to the same tool registry. This calls a real provider."""
import argparse
from miniagent import Harness, Policy, get_skill, list_skills
from miniagent.config import load_config
from miniagent.plugins import coding_tools


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", help="provider:model-id")
    parser.add_argument("skill", choices=list_skills())
    parser.add_argument("prompt")
    args = parser.parse_args()
    cfg = load_config(model_override=args.model)
    app = Harness(model=cfg.llm.model, providers=cfg.providers, api_key=cfg.llm.api_key,
                  base_url=cfg.llm.api_base, temperature=cfg.llm.temperature,
                  policy=Policy(mode="readonly"))
    app.use(coding_tools())
    app.apply_skill(get_skill(args.skill))
    print(app.run(args.prompt))


if __name__ == "__main__":
    main()
