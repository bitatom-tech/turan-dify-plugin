# Turan for Dify

Turn product images into model styling, campaign visuals, patterns and videos directly in your Dify workflows.

Turan v0.1.0 includes 29 creative tools across five categories, plus a tool for recovering existing task results. Configure your Turan API Key once to use all available tools.

[Source repository](https://github.com/bitatom-tech/turan-dify-plugin) · [Simplified Chinese guide](readme/README_zh_Hans.md) · [Privacy policy](PRIVACY.md)

Publisher: `bitatom` · Plugin ID: `bitatom/turan` · Version: `0.1.0`

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
3. Sign in to [Turan](https://turan.design/), or register an account if needed.
4. Open [API Key management](https://turan.design/user-center/api-key), create a key and copy it.
5. Open the Turan plugin's authorization settings in Dify, enter your API Key and save.

Your Turan account needs sufficient credits. Local-package installation is subject to your Dify administrator's plugin policy. If installation is blocked by signature verification, contact the administrator.

## Connection requirements

The Dify plugin runtime needs access to:

- Your Dify file service, to read the files selected in the workflow. For self-hosted Dify, the administrator must configure file-service URLs reachable from the plugin runtime.
- `https://turan.design` and `https://www.turan.design`, for account authorization, tool configuration, image uploads and generation tasks.
- `https://rh-hk-images.xiaoyaoyou.com`, for result files returned by Turan. Results hosted on the two Turan domains are also supported.

The API Key is sent only to the approved Turan API and upload endpoints. Result downloads do not include it. The plugin accepts Dify file inputs rather than arbitrary image URL parameters.

## Build a workflow

1. Add a file input to your workflow's Start node for the source image.
2. Add a Turan tool and bind its image inputs to the relevant file variables.
3. Set the creative instructions, output specification and other business parameters.
4. Connect the tool's `files` output to the next node or the workflow's Output node.
5. Run the workflow. The tool waits for generation and returns the resulting files when ready.

Image inputs support PNG, JPEG and WebP, up to 20 MiB each.

Reference images use one multi-image upload input. Upload just the images you need; each tool shows its maximum count. Their list order follows the corresponding image positions on Turan.

Aspect ratio and specification are text parameters that accept literal values or upstream variables. Each parameter name shows its default; its help text lists that tool's allowed values and reference specification prices. Use the exact values shown; available values vary by tool and are validated before submission. Keep API values as shown even when an option uses a Chinese value.

Tools return generated images or video through `files`, together with `task_id`, `workflow_code`, `status` and `result_count` when available.

## Credits and pricing

Usage is billed to the Turan account associated with your API Key. The plugin has no separate credit balance. Available specifications and reference costs appear in each tool; final pricing is confirmed by Turan at submission.

## Recover a task result

If a workflow is interrupted or does not receive its files, keep the original task ID. Add **Recover existing task result**, enter that ID and use its `files` output. Recovery retrieves the existing task without starting another generation. It does not automatically resume an already failed workflow.

Each tool invocation waits up to eight minutes. Your Dify workflow or network may have additional execution limits. Disable automatic retries on generation nodes to avoid creating another task when an earlier submission is uncertain.

## Privacy

The plugin sends the images and parameters you select to Turan to perform the requested generation. Images and instructions may contain personal information. Review the [plugin privacy policy](PRIVACY.md) and [Turan service privacy policy](https://turan.design/login/register) before submitting them. On the Turan page, select **Privacy Policy** to open the policy; it is displayed in a dialog.

The plugin keeps only the latest task-recovery record per credential namespace in Dify storage. Retention of files, workflow records and Turan service data is explained in the privacy policy.

## Support

Report bugs and request features through [GitHub Issues](https://github.com/bitatom-tech/turan-dify-plugin/issues). Do not include API keys or personal images in public reports.

Contact: [bitatom_tech@163.com](mailto:bitatom_tech@163.com).

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
