# Hermes integration

This folder holds the pieces that connect agentskill-kit to [Hermes Agent](https://github.com/NousResearch/hermes-agent).

## Use skills with Hermes

Export any skill from this repository to the Hermes skills folder:

```bash
askit export skills/log-analyzer --target hermes --global
```

This copies the skill to `~/.hermes/skills/log-analyzer/`. To install straight from the registry:

```bash
askit install log-analyzer --target hermes --global
```

## The skill-forge playbook

`skills/skill-forge/` teaches a Hermes agent to turn repeated work into a tested skill and to check the result with
`askit lint`, `askit scan`, `askit test` and `askit score` instead of grading itself.

```bash
askit export integrations/hermes/skills/skill-forge --target hermes --global
```

## Training environment

`skill_forge_env.py` is an Atropos environment with five authoring scenarios and a reward function. The reward
function can use a verified score computed by agentskill-kit instead of the number the agent reports:

```python
from skill_forge_env import SkillForgeEnv, SCENARIOS

env = SkillForgeEnv()
scenario = env.get_next_item()
result = env.evaluate(trajectory, scenario, skill_dir="~/.hermes/skills/web-summarizer")
print(result["total_reward"])
```

`skill_forge_config.yaml` is a starting point for an Atropos run. Copy this folder next to your Atropos
environments and adjust the class path to your layout.
