# Privacy notice — Turan

The plugin sends images and business parameters explicitly supplied to its tools to
Turan production (https://turan.design/api and the verified upload endpoint at
https://www.turan.design/api). The configured API Key authenticates only these requests.
Image/video results are downloaded without the API Key and returned to Dify.
The plugin package never contains an account key.

Dify manages encrypted provider credentials. The plugin stores only the latest task ID,
workflow code, timestamp, output type and quote per hashed credential namespace. This
record is overwritten by later submissions and removed through the host storage lifecycle.
No fixed automatic expiry is claimed. The plugin does not persist image bytes, prompts,
plaintext API keys or signed file URLs, and adds no telemetry. Errors are bounded and
credentials/URLs redacted before being returned.

Images and task history stored by Turan, and files stored by Dify, follow those services'
policies. Removing the plugin does not cancel tasks or delete service data. Review Turan
and your Dify operator's policies before processing personal images.

