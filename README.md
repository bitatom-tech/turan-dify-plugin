# Turan for Dify

Turn product images into model styling, campaign visuals, patterns and videos directly in your Dify workflows.

Turan v0.1.0 includes 29 creative tools across five categories, plus a tool for recovering existing task results. Configure your Turan API Key once to use all available tools.

[Source repository](https://github.com/bitatom-tech/turan-dify-plugin) · [Simplified Chinese guide](readme/README_zh_Hans.md)

## Creative tools

| Category | Examples |
| --- | --- |
| Design Materials | Background removal, garment recoloring, product details, product highlights grids |
| Model Tools | Outfit changes, virtual models, pose changes, lifestyle images |
| Scene Creativity | Promotional posters, sports scenes, brand campaigns, style cloning |
| Pattern Tools | Flat lay to 3D, local image editing, pattern extraction, seamless fabric patterns |
| Video | Product video generation |

## Install and connect

1. Open **Plugins** in Dify and choose **Install from local package**.
2. Select `turan-0.1.0.difypkg` and complete installation.
3. Get an API Key from your [Turan account](https://turan.design/user-center/api-key).
4. Open the Turan plugin's authorization settings, enter your API Key and save.

Your Turan account needs sufficient credits. Local-package installation is subject to your Dify administrator's plugin policy. If installation is blocked by signature verification, contact the administrator.

## Build a workflow

1. Add a file input to your workflow's Start node for the source image.
2. Add a Turan tool and bind its image inputs to the relevant file variables.
3. Set the creative instructions, output specification and other business parameters.
4. Connect the tool's `files` output to the next node or the workflow's Output node.
5. Run the workflow. The tool waits for generation and returns the resulting files when ready.

Image inputs support PNG, JPEG and WebP, up to 20 MiB each.

Reference images use one multi-image upload input. Upload just the images you need; each tool shows its maximum count. Their list order follows the corresponding image positions on Turan.

Aspect ratio and specification are text parameters that accept literal values or upstream variables. Each parameter name shows its default; guidance below lists that tool's allowed values and reference specification prices. Use the exact values shown; available values vary by tool and are validated before submission.

## Credits and pricing

Usage is billed to the Turan account associated with your API Key. The plugin has no separate credit balance. Available specifications and reference costs appear in each tool; final pricing is confirmed by Turan at submission.

## Recover a task result

If a workflow is interrupted or does not receive its files, keep the original task ID. Add **Recover existing task result**, enter that ID and use its `files` output. Recovery retrieves the existing task without starting another generation. It does not automatically resume an already failed workflow.

Each tool invocation waits up to eight minutes. Your Dify workflow or network may have additional execution limits. Disable automatic retries on generation nodes to avoid creating another task when an earlier submission is uncertain.

Visit [Turan](https://turan.design/) for account information. See [PRIVACY.md](PRIVACY.md) for data handling details.

## Support

Report bugs and request features through [GitHub Issues](https://github.com/bitatom-tech/turan-dify-plugin/issues). Do not include API keys or personal images in public reports.

## Build and test

Python 3.12 is required. Install runtime and test dependencies, then run the offline test suite:

```sh
python -m pip install -r requirements-dev.txt
python -m pytest tests -q
```

To build an installable package with the Dify plugin CLI, run this from the parent directory:

```sh
dify plugin package ./turan-dify-plugin
```

The package contains the plugin runtime and documentation. Tests and development scripts are excluded by `.difyignore`.
