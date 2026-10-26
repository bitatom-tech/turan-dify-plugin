# Privacy Policy — Turan for Dify

This policy describes data handled by the Turan Dify plugin published under `bitatom/turan`. The plugin connects your Dify workflows to the Turan service operated by Qimo Technology (Guangzhou) Co., Ltd. and its affiliates.

## Data processed and purposes

The plugin processes the following data to carry out the tools you invoke:

| Data | Purpose and destination |
| --- | --- |
| Your Turan API Key | Authenticate with Turan and use the associated account's credits. Dify manages the configured provider credential; the plugin reads it during a request. |
| Selected image files and filenames | Read the files from your Dify file service and upload them to Turan for the requested image or video generation. |
| Business parameters | Send your instructions, color values, aspect ratio, specification and other selected tool parameters to Turan to configure generation. |
| Task ID and task metadata | Query task progress, retrieve results and support recovery of an existing task. A task ID supplied to the recovery tool is sent to Turan, which checks access using your API Key. |
| Generated images, video and result metadata | Download the result files returned by Turan and provide them to Dify for use by your workflow. |

Images may show identifiable people, including faces, and instructions may contain personal information. Submit only content you are authorized to process and share with Turan. The plugin does not require access to your contacts, browsing history, location, camera or microphone.

## Recipients and network access

The plugin communicates with:

- Your Dify deployment and its configured file service, to read selected inputs and return outputs.
- `https://turan.design/api`, for authorization, tool configuration and task operations, and the approved image-upload endpoint on `https://turan.design` or `https://www.turan.design`.
- Turan result storage on `https://rh-hk-images.xiaoyaoyou.com`, `https://turan.design` or `https://www.turan.design`, to download the generated files.

The Turan API Key is included only in requests to the approved Turan API and upload endpoints. It is not sent to your Dify file service or included in result-download requests. Result downloads and their redirects are restricted to the listed result hosts.

Turan receives the submitted content and parameters and handles service-side processing and storage. Its service policy describes sharing with authorized partners needed to provide the service, subject to confidentiality and security obligations. Review the [Turan service privacy policy](https://turan.design/login/register): select **Privacy Policy** on the login or registration page to open the policy dialog. This is the website's policy entry point rather than a standalone policy page.

For Dify Cloud, also review the [Dify privacy policy](https://dify.ai/legal/privacy-policy). For another Dify deployment, ask its operator about the policies that apply to uploaded files, workflow records, backups and logs.

## Plugin storage and logs

The plugin stores one latest task-recovery record per API-Key-derived hashed namespace in Dify plugin storage. The record contains the task ID, workflow code, creation timestamp, output type and pricing metadata. A new submitted task overwrites that namespace's previous record.

The plugin does not persist image or video bytes, instruction text, plaintext API Keys or signed file URLs in its own task storage. It does not add analytics or telemetry. Input files and result bytes are processed in memory during a tool invocation. Dify may separately retain workflow inputs, outputs and execution records according to its deployment settings.

Public plugin errors redact API Keys and URLs and limit returned service-error details. The plugin does not intentionally log submitted image content, instructions or credentials; Dify and Turan maintain their own service records under their respective policies.

## Retention and deletion

- **Plugin recovery record:** retained until overwritten by a later submission or removed through the Dify host's storage lifecycle or administrator action. The plugin does not set a fixed automatic expiry or provide a separate record-deletion tool.
- **Dify data:** uploaded files, generated outputs, execution records and backups follow your Dify deployment's retention and deletion settings. Contact your Dify operator to manage these records.
- **Turan data:** the Turan service policy states that personal information is retained only as necessary for its stated purposes and any period required by law. It does not specify a fixed number of days for this plugin's source images, generated files or task history. This plugin does not promise a shorter service-side retention period.

Turan's policy provides for access, correction, eligible deletion and account-cancellation requests through available Turan functions or by contacting Turan at **400-823-3655**. Requests may require identity verification and are subject to applicable legal retention requirements. Consult the current service policy for the conditions.

Removing the plugin or its authorization does not cancel an already submitted task or delete content held by Turan or Dify. Revoking the API Key through Turan prevents future authenticated use of that key but is not a data-deletion request.

## Contact

For Turan account or service-data requests, use the contact methods in the [Turan service privacy policy](https://turan.design/login/register). For plugin issues, email [bitatom_tech@163.com](mailto:bitatom_tech@163.com) or use [GitHub Issues](https://github.com/bitatom-tech/turan-dify-plugin/issues). Public issue reports must not include API Keys, private images or other personal information.
