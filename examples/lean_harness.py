"""Run with a configured provider:model-id and its provider-specific key."""
import argparse

from miniagent import Harness
from miniagent.plugins import coding_tools
from miniagent.policy import Policy
from miniagent.session import Session

parser = argparse.ArgumentParser()
parser.add_argument("model")
parser.add_argument("prompt")
parser.add_argument("--session", required=True)
args = parser.parse_args()
app = Harness(model=args.model, policy=Policy(mode="readonly"), session=Session(args.session))
app.use(coding_tools())
print(app.run(args.prompt))
