# VAST Intersight Automation for Node Assignment

`vast-intersight-profile-automation` automates the full Cisco Intersight node-assignment lifecycle for standalone environments.

The main workflow on this repository is:

1. Build or refresh the baseline organization, policies, and server profile template.
2. Derive server profiles using serial-based profile naming.
3. Assign those derived profiles to claimed servers by serial number.
4. Deploy the successfully assigned profiles in batch.
5. Capture runtime artifacts for derive, assign, and deploy results.

The automation is driven from `group_vars/all.yml`. The policy and template playbooks are still part of the repository, but they exist to support the end-to-end node-assignment and deployment flow described in this README.

## Repository layout

- `playbooks/build_standalone_template.yml`: build the baseline organization, policies, and template used for node assignment
- `playbooks/configure_server_profiles.yml`: derive server profiles from the template
- `playbooks/assign_server_profiles.yml`: assign derived profiles to servers by serial number
- `playbooks/deploy_server_profiles.yml`: deploy successfully assigned profiles
- `roles/intersight_organization/`: organization create and default-org sharing
- `roles/intersight_policy_catalog/`: policy creation
- `roles/intersight_server_profile_templates/`: template creation
- `roles/intersight_server_profiles/`: derive, assign, and deploy profile lifecycle logic
- `group_vars/all.yml`: main user inputs
- `requirements.yml`: required Ansible collection

## Getting started

Clone the repository and install the required collection:

```bash
git clone https://github.com/<your-github-username>/vast-intersight-profile-automation.git
cd vast-intersight-profile-automation

export REPO_HOME="$PWD"
export INTERSIGHT_API_KEY_ID="your-api-key-id"
export INTERSIGHT_API_PRIVATE_KEY_PATH="/tmp/intersight-clean-ec.pem"
export INTERSIGHT_API_ENDPOINT="https://intersight.com"

ansible-galaxy collection install -r requirements.yml
```

After that, follow the fast path or the stage-by-stage sections below.

## Prerequisites

- Ansible installed
- `cisco.intersight` collection installed
- Cisco Intersight API key ID
- Cisco Intersight private key
- Access to the target Intersight account

Install the collection:

```bash
ansible-galaxy collection install -r requirements.yml
```

Set environment variables:

```bash
export REPO_HOME="$HOME/path/to/your/repo"
export INTERSIGHT_API_KEY_ID="your-api-key-id"
export INTERSIGHT_API_PRIVATE_KEY_PATH="/tmp/intersight-clean-ec.pem"
export INTERSIGHT_API_ENDPOINT="https://intersight.com"
```

You can also use an untracked local vars file:

1. Copy `.intersight.local.yml.example` to `.intersight.local.yml`
2. Put your real credentials there
3. Run the playbooks normally

Before the first live run in any new Intersight account, run the dedicated
authentication preflight:

```bash
cd "$REPO_HOME"
ANSIBLE_LOCAL_TEMP=/tmp ANSIBLE_REMOTE_TEMP=/tmp ansible-playbook playbooks/test_intersight_auth.yml \
  -e intersight_organization=default
```

This preflight does three things:

- validates that the private key file exists
- validates that OpenSSL can parse the private key
- performs a signed organization lookup using the repo helper script, which is
  the same lookup path used by the core workflow

If the private key fails with a deserialize or ASN.1 parsing error, normalize it once and point `.intersight.local.yml` to the cleaned file:

```bash
mkdir -p "$HOME/.intersight"
openssl ec -in "/path/to/original-private-key.pem" -out "$HOME/.intersight/intersight-clean-ec.pem" -param_enc named_curve
```

Then set:

```yaml
intersight_api_private_key_path: "$HOME/.intersight/intersight-clean-ec.pem"
```

Why this happens:

- Cisco Intersight API keys are EC keys, and different PEM encodings of the
  same key are not always handled consistently by every Python and Ansible
  crypto path.
- A key can parse in one tool and still fail in another with ASN.1 or
  deserialize errors.
- A separate failure mode is a 401 from Intersight when the key ID, private
  key, account, or endpoint region do not match.

The repo is now hardened to avoid the fragile organization lookup path, but
users should still normalize the private key once and run the preflight before
their first baseline build in a new account.

## Fast path

If you want the current default workflow for node assignment, use these commands with `intersight_organization=default`.

1. Build the baseline organization resources, policies, and server profile template:

```bash
cd "$REPO_HOME"
export INTERSIGHT_API_ENDPOINT="https://intersight.com"

ANSIBLE_LOCAL_TEMP=/tmp ANSIBLE_REMOTE_TEMP=/tmp ansible-playbook playbooks/build_standalone_template.yml \
  -e intersight_apply_changes=true \
  -e intersight_organization=default \
  -e intersight_create_organization_if_missing=false \
  -e intersight_include_default_organization=false
```

2. Derive serial-based server profiles from the template:

```bash
ANSIBLE_LOCAL_TEMP=/tmp ANSIBLE_REMOTE_TEMP=/tmp ansible-playbook playbooks/configure_server_profiles.yml \
  -e intersight_apply_changes=true \
  -e intersight_organization=default
```

3. Review the derive artifact:

```bash
cat artifacts/derived_server_profiles.json
```

4. Assign the derived profiles to the serial numbers listed in `group_vars/all.yml`:

```bash
ANSIBLE_LOCAL_TEMP=/tmp ANSIBLE_REMOTE_TEMP=/tmp ansible-playbook playbooks/assign_server_profiles.yml \
  -e intersight_apply_changes=true \
  -e intersight_organization=default
```

5. Review the assignment artifact:

```bash
cat artifacts/assigned_server_profiles.json
```

6. Deploy the successfully assigned profiles in batch:

```bash
ANSIBLE_LOCAL_TEMP=/tmp ANSIBLE_REMOTE_TEMP=/tmp ansible-playbook playbooks/deploy_server_profiles.yml \
  -e intersight_apply_changes=true \
  -e intersight_organization=default \
  -e intersight_server_profile_deploy_wait=true
```

7. Review the deploy artifact:

```bash
cat artifacts/deployed_server_profiles.json
```

Everything else will use the defaults from `group_vars/all.yml`, including `intersight_server_serial_numbers`.

## Full workflow

1. Configure credentials and endpoint.
2. Set organization and serial-number inputs in `group_vars/all.yml`.
3. Build the baseline policies and template with `playbooks/build_standalone_template.yml`.
4. Verify that the template exists in Intersight.
5. Run `playbooks/configure_server_profiles.yml` to derive serial-based server profiles and refresh the derive artifact.
6. Run `playbooks/assign_server_profiles.yml` to assign the derived profiles to the configured serial numbers.
7. Review `artifacts/assigned_server_profiles.json` and fix any failed serial mappings.
8. Run `playbooks/deploy_server_profiles.yml` to deploy the successfully assigned profiles.

This repository treats these as three separate execution stages on purpose:

- `configure_server_profiles.yml` derives only
- `assign_server_profiles.yml` assigns only
- `deploy_server_profiles.yml` deploys only


## Main inputs

Common inputs in `group_vars/all.yml`:

- `intersight_apply_changes`
- `intersight_organization`
- `intersight_organization_description`
- `intersight_create_organization_if_missing`
- `intersight_include_default_organization`
- `intersight_default_organization_name`
- `intersight_organization_moid` (advanced override)
- `intersight_policy_name_prefix`
- `intersight_template_name_prefix`
- `intersight_profile_name_prefix`
- `intersight_server_profile_assignments`
- `intersight_server_profile_deploy_profile_names`
- `intersight_server_profile_proceed_on_reboot`
- `intersight_server_profile_artifact_path`
- `intersight_server_profile_assign_artifact_path`
- `intersight_server_profile_deploy_artifact_path`

`intersight_apply_changes` is the safety gate. Keep it `false` until you want to write to Intersight.

Use `intersight_organization` as the normal user input. `intersight_organization_moid` is an advanced override for cases where you want to target a specific organization object directly and skip name-based lookup. Most users should leave it empty.

For the profile lifecycle on this branch:

- `intersight_number_of_profiles` is an optional override for non-serial derive runs.
- `intersight_server_profile_assignments` controls which derived profile is assigned to which server serial number.
- `intersight_server_profile_deploy_profile_names` controls which already-assigned profile is activated.
- `intersight_server_profile_artifact_path` stores the last derived profile names for later reuse.
- `intersight_server_profile_assign_artifact_path` stores assignment results written by the assign playbook.
- `intersight_server_profile_deploy_artifact_path` stores the final deploy results written by the deploy playbook.
- The assign step and the deploy step must reference the same derived profile name.

## Artifact files

The profile workflow writes runtime artifact files under `artifacts/`. These files are produced during playbook execution and are intended for validation, stage-to-stage reuse, and failure analysis.

The main artifact files are:

- `artifacts/derived_server_profiles.json`
- `artifacts/assigned_server_profiles.json`
- `artifacts/deployed_server_profiles.json`

`derived_server_profiles.json` is written by `playbooks/configure_server_profiles.yml`. It stores the target organization, template information, and the derived profile names. The assign flow can reuse this file when you do not provide explicit profile names.

`assigned_server_profiles.json` is written by `playbooks/assign_server_profiles.yml`. It stores one entry per attempted assignment, including:

- `profile_name`
- `server_serial_number`
- `status`
- `success`
- `error`
- `error_description`

`deployed_server_profiles.json` is written by `playbooks/deploy_server_profiles.yml`. It stores one entry per attempted deployment, including:

- `profile_name`
- `status`
- `server_serial_number`
- `error`
- `error_description`

Each artifact also stores the `organization` used for that run. Assign fallback reuses the derived-profile artifact only when its saved `organization` matches the current `intersight_organization`. Deploy fallback reuses the assignment artifact only when its saved `organization` matches the current `intersight_organization`.

## Failure analysis

These artifacts are intended to help analyze failures without relying only on console output.

For assignment failures:

- If the server serial number cannot be resolved in Intersight, the assign playbook records a failed entry in `artifacts/assigned_server_profiles.json`, continues with the remaining profiles, and fails once at the end of the batch.
- If the target profile name cannot be resolved in the selected organization, the assign playbook records a failed entry, continues with the remaining profiles, and fails once at the end of the batch.
- If the derive-stage artifact belongs to a different organization, the assign playbook fails early before reusing stale profile names.

For deployment failures:

- If the deploy stage reaches a terminal failed state, the deploy playbook writes that final status and error context into `artifacts/deployed_server_profiles.json`, continues with the remaining profiles, and fails once at the end of the batch.
- If the deploy stage succeeds, the deploy artifact records the completed status and the assigned server serial number.
- If the deploy stage is already in progress or already complete, the playbook does not submit a duplicate activation request; it checks the current profile state and records the result.
- If the assignment-stage artifact belongs to a different organization, the deploy playbook fails early instead of reusing profile names from the wrong org.

Recommended troubleshooting flow:

1. Check `artifacts/derived_server_profiles.json` to confirm the exact profile names created for the selected organization.
2. Check `artifacts/assigned_server_profiles.json` to confirm each profile-to-serial mapping and identify any serial lookup failures.
3. Check `artifacts/deployed_server_profiles.json` to confirm the final deployment status for each profile.
4. Compare the artifact contents with the corresponding profile state in the Intersight UI when deeper validation is needed.

Quick summary commands:

```bash
jq '.profiles[] | {profile_name, status, success, server_serial_number, error_description}' artifacts/assigned_server_profiles.json
```

```bash
jq '.profiles[] | {profile_name, status, success, server_serial_number, error_description}' artifacts/deployed_server_profiles.json
```

```bash
jq '.target_profile_names' artifacts/derived_server_profiles.json
```


## Supporting baseline build

The current project is centered on profile derivation, node assignment, and deployment. The organization, policy, and template playbooks remain part of the repository because they build the baseline objects that the assignment flow depends on.

## 1. Organization baseline

The organization role does the following:

- looks up the target organization by name
- creates it if it does not exist and creation is allowed
- refreshes and reapplies the org metadata after create
- optionally shares resources from the `default` organization into the target org

The share toggle is:

- `intersight_include_default_organization: true`

That creates the Intersight sharing rule so the target org can consume shared resources from `default`.

Set the organization name in `group_vars/all.yml` with:

```yaml
intersight_organization: "your-org-name"
```

Test only the organization flow:

```bash
cd "$REPO_HOME"
export INTERSIGHT_API_ENDPOINT="https://intersight.com"
ANSIBLE_LOCAL_TEMP=/tmp ANSIBLE_REMOTE_TEMP=/tmp ansible-playbook playbooks/test_org.yml \
  -e intersight_organization=create-new-org \
  -e intersight_create_organization_if_missing=true \
  -e intersight_include_default_organization=true
```

Actual organization-backed build command for normal use:

```bash
cd "$REPO_HOME"
export INTERSIGHT_API_ENDPOINT="https://intersight.com"
ANSIBLE_LOCAL_TEMP=/tmp ANSIBLE_REMOTE_TEMP=/tmp ansible-playbook playbooks/build_standalone_template.yml \
  -e intersight_apply_changes=true \
  -e intersight_organization=create-new-org \
  -e intersight_create_organization_if_missing=true \
  -e intersight_include_default_organization=true
```

This is the normal user flow when the target organization may need to be created and shared before policies and template are built.

## 2. Policy baseline

The policy catalog currently builds these standalone policies:

- BIOS
- Boot Order
- Power
- IPMI over LAN
- Local User
- Serial over LAN
- Virtual KVM
- Storage
- Thermal
- NTP

Policy names are driven by `intersight_policy_name_prefix`. By default they are created as:

- `auto-vast-bios`
- `auto-vast-bootorder`
- `auto-vast-power`
- `auto-vast-ipmi`
- `auto-vast-localuser`
- `auto-vast-sol`
- `auto-vast-vkvm`
- `auto-vast-storage`
- `auto-vast-thermal`
- `auto-vast-ntp`

These policy definitions live in `group_vars/all.yml` under `intersight_policy_catalog`.

With the current defaults, the Thermal Policy is created as `auto-vast-thermal`
with `FanControlMode: HighPower`.

The NTP Policy is also user-driven from `group_vars/all.yml`:

- `intersight_ntp_servers`
- `intersight_ntp_timezone`

With the current checked-in setup, the NTP Policy uses:

- `intersight_ntp_servers: ["172.22.251.23"]`
- `intersight_ntp_timezone: "America/Los_Angeles"`

For a generic environment, you can change the NTP server list to values such as:

- `time.google.com`

Build the full policy set with:

```bash
cd "$REPO_HOME"
export INTERSIGHT_API_ENDPOINT="https://intersight.com"
ANSIBLE_LOCAL_TEMP=/tmp ANSIBLE_REMOTE_TEMP=/tmp ansible-playbook playbooks/build_policies.yml \
  -e intersight_apply_changes=true \
  -e intersight_organization=default \
  -e intersight_create_organization_if_missing=false \
  -e intersight_include_default_organization=false
```

This creates all policies defined under `intersight_policy_catalog` without creating the template.

You can also run the targeted policy test playbooks individually:

- `playbooks/test_auto_bios.yml`
- `playbooks/test_auto_bootorder.yml`
- `playbooks/test_auto_power.yml`
- `playbooks/test_auto_storage.yml`
- `playbooks/test_auto_sol.yml`
- `playbooks/test_auto_vkvm.yml`
- `playbooks/test_auto_ipmi.yml`
- `playbooks/test_auto_local_user.yml`
- `playbooks/test_auto_thermal.yml`
- `playbooks/test_auto_ntp.yml`

## 3. Template baseline

The server profile template role:

- resolves the policy MOIDs in the target org
- attaches the policy bucket to the template
- creates or updates the standalone template

`playbooks/build_standalone_template.yml` runs the full baseline flow for this stage:

- organization handling
- policy creation or update
- template creation or update

So it does not assume the policies already exist. It creates or updates them first, then builds the template.

The current template input is in `group_vars/all.yml` under `intersight_server_profile_templates`.

By default the template name is:

- `auto-vast-template`

With the current defaults, this template attaches the full baseline policy set,
including `auto-vast-thermal` and `auto-vast-ntp`.

Build the full standalone baseline, including template:

```bash
cd "$REPO_HOME"
export INTERSIGHT_API_ENDPOINT="https://intersight.com"
ANSIBLE_LOCAL_TEMP=/tmp ANSIBLE_REMOTE_TEMP=/tmp ansible-playbook playbooks/build_standalone_template.yml \
  -e intersight_apply_changes=true \
  -e intersight_organization=default \
  -e intersight_create_organization_if_missing=false \
  -e intersight_include_default_organization=false
```

For a non-default org:

- set `intersight_organization`
- set `intersight_create_organization_if_missing: true`
- set `intersight_include_default_organization: true` if the org should consume shared resources from `default`

## 4. Derive profiles

The derive flow creates server profiles from an existing template by using the same `bulk.MoCloner` pattern used by the Intersight UI.

The derive flow does not guess the template. It uses the `template_name` value defined under `intersight_server_profiles` in `group_vars/all.yml`. With the current defaults, that resolves to `auto-vast-template`.

Current user-facing inputs:

- `template_name`
- `base_name`
- `description`
- `organization`
- `serial_numbers`
- `start_index`
- `auto_start_index`
- optional `intersight_number_of_profiles`

If `auto_start_index: false`, the derive flow starts at `start_index`.

If `auto_start_index: true`, the derive flow:

- reads existing server profiles in the target org
- finds names matching `base_name_DERIVED-<number>`
- starts at the next available suffix

If `serial_numbers` is set, the derive flow names profiles as `base_name_<serial>` and ignores suffix-based numbering.

Example server profile inputs in `group_vars/all.yml`:

```yaml
intersight_server_profiles:
  - template_name: "{{ intersight_template_name_prefix }}vast-template"
    base_name: "{{ intersight_template_name_prefix }}vast-template"
    start_index: 1
    auto_start_index: true
    description: "derive profiles from AUTO"
    organization: "{{ intersight_organization }}"
    serial_numbers: "{{ intersight_server_serial_numbers }}"
    tags: []
```

Run the derive flow:

```bash
cd "$REPO_HOME"
export INTERSIGHT_API_ENDPOINT="https://intersight.com"
ANSIBLE_LOCAL_TEMP=/tmp ANSIBLE_REMOTE_TEMP=/tmp ansible-playbook playbooks/configure_server_profiles.yml \
  -e intersight_apply_changes=true \
  -e intersight_organization=default
```

This playbook is derive-only. It does not assign servers and it does not deploy profiles.

After the derive run, check the artifact to confirm the exact derived profile names:

```bash
cat artifacts/derived_server_profiles.json
```

The assign step can reuse that artifact automatically when you are following the serial-based flow.

Defaults:

- `start_index` default is `1`
- `auto_start_index` default is `true`

So by default the profile flow creates one derived profile starting at the next available suffix.

If you also provide `intersight_server_serial_numbers`, the derive-only playbook keeps those values available for naming and creates profiles like `auto-vast-template_WZP2949ACDB` without performing assignment in the same run.

If you are not using serial-based naming and want more than one derived profile, set `intersight_number_of_profiles` or `number_of_profiles` explicitly.


## 5. Assign nodes

The assign-node flow assigns existing server profiles to claimed servers by resolving each server serial number to a server MOID and then updating the server profile with `assigned_server`.

There are two supported input modes in `group_vars/all.yml`:

1. Explicit assignment mappings

```yaml
intersight_server_profile_assignments:
  - profile_name: "auto-vast-template_WZP2949ACDB"
    server_serial_number: "WZP2949ACDB"
```

2. Serial-number-only assignment

```yaml
intersight_server_serial_numbers:
  - "SERIAL1"
  - "SERIAL2"

intersight_server_profile_artifact_path: "{{ playbook_dir | default('.') }}/../artifacts/derived_server_profiles.json"
intersight_server_profile_assign_artifact_path: "{{ playbook_dir | default('.') }}/../artifacts/assigned_server_profiles.json"
```

In serial-number-only mode, the assign-server playbook reads the saved artifact from the earlier profile-derive run and maps the saved profile names to the serial numbers in order. When the derive run also used those serial numbers for naming, the saved names will already be `base_name_<serial>`.

Important behavior:

- Explicit assignment mode works with any existing server profile, including profiles created manually in the Intersight UI.
- The artifact is populated only by `playbooks/configure_server_profiles.yml`.
- Serial-number-only assignment works only when that artifact exists and contains derived profile names.
- Serial-number-only assignment reuses the artifact only when its saved `organization` matches `intersight_organization`.
- The assign playbook writes `artifacts/assigned_server_profiles.json` on both success and failure, including the profile name, server serial number, status, and detailed error text.
- The assign playbook continues through all requested profiles and fails only after the full batch has been processed if any assignment failed.
- If you provide only serial numbers and the artifact is missing or empty, the assign-server playbook fails early instead of guessing which profiles to use.

Run the assign-node flow with:

```bash
cd "$REPO_HOME"
export INTERSIGHT_API_ENDPOINT="https://intersight.com"
ANSIBLE_LOCAL_TEMP=/tmp ANSIBLE_REMOTE_TEMP=/tmp ansible-playbook playbooks/assign_server_profiles.yml \
  -e intersight_apply_changes=true \
  -e intersight_organization=default
```

Expected result:

- Explicit mode assigns each named profile to the server with the matching serial number.
- Serial-number-only mode assigns the saved derived profiles from the artifact in order.
- The assign playbook fails early only when required input artifacts are missing or belong to the wrong organization.
- Individual profile lookup or serial lookup failures are recorded in the assignment artifact, and the batch continues.


## 6. Deploy Profiles

The deploy flow is the step after node assignment. It updates an assigned `server.Profile` with the same scheduled-action pattern used by the Intersight UI to start activation on the server.

Optional explicit user-facing inputs in `group_vars/all.yml`:

```yaml
intersight_server_profile_deploy_profile_names:
  - "auto-vast-template_WZP2949ACDB"
intersight_server_profile_proceed_on_reboot: true
intersight_server_profile_deploy_wait: true
intersight_server_profile_deploy_wait_initial_delay_seconds: 300
intersight_server_profile_deploy_wait_poll_seconds: 60
intersight_server_profile_deploy_wait_timeout_seconds: 1800
intersight_server_profile_deploy_artifact_path: "{{ playbook_dir | default('.') }}/../artifacts/deployed_server_profiles.json"
```

Use `intersight_server_profile_deploy_profile_names` only when you want to override the default artifact-based deploy target list.

By default, the deploy playbook reads `artifacts/assigned_server_profiles.json` and selects only profiles with:

- `success: true`
- `status: "Assigned"`

Run the deploy flow with:

```bash
cd "$REPO_HOME"
export INTERSIGHT_API_ENDPOINT="https://intersight.com"
ANSIBLE_LOCAL_TEMP=/tmp ANSIBLE_REMOTE_TEMP=/tmp ansible-playbook playbooks/deploy_server_profiles.yml \
  -e intersight_apply_changes=true \
  -e intersight_organization=default \
  -e intersight_server_profile_deploy_wait=true
```

Run the deploy flow without waiting for completion:

```bash
cd "$REPO_HOME"
export INTERSIGHT_API_ENDPOINT="https://intersight.com"
ANSIBLE_LOCAL_TEMP=/tmp ANSIBLE_REMOTE_TEMP=/tmp ansible-playbook playbooks/deploy_server_profiles.yml \
  -e intersight_apply_changes=true \
  -e intersight_organization=default \
  -e intersight_server_profile_deploy_wait=false
```

Important:

- If `intersight_server_profile_deploy_profile_names` is empty, the deploy playbook reuses the successfully assigned profile names from `artifacts/assigned_server_profiles.json`.
- That assignment artifact is reused only when its saved `organization` matches `intersight_organization`.
- The deploy step must target the same derived profile names used by the assign step.
- Only assignment entries with `success: true` and `status: "Assigned"` are selected automatically for deploy fallback.
- `intersight_server_profile_deploy_wait=true` is the default mode and waits for completion before exiting.
- `intersight_server_profile_deploy_wait=false` submits the deploy request, captures the current status, writes the deploy artifact, and returns without waiting for completion.
- By default the deploy playbook first kicks off deployment for all selected profiles, then waits 5 minutes before the first status check, then keeps polling until completion and writes `artifacts/deployed_server_profiles.json` with `profile_name`, final `status`, `server_serial_number`, and detailed error text.
- The deploy wait logic does not treat `DeployStatus: Complete` by itself as final success. A profile is treated as fully complete only after it reaches the settled post-deploy state with `ConfigState: Associated` and `ControlAction: No-op`.
- The deploy playbook continues through all requested profiles and fails only after the full batch has been processed if any deployment failed.
- Deployment is asynchronous in Intersight, so the profile can remain in a deploying or configuring state for some time after the playbook returns.
- If a profile is already deployed, the playbook skips the duplicate activation request.

Expected result:

- Sends the deploy request to the selected assigned profiles.
- Sets `ProceedOnReboot` from `intersight_server_profile_proceed_on_reboot`.
- Starts the profile activation workflow in Intersight and records the result in the deploy artifact.


## 7. Software Repository

The software repository flow creates or updates Intersight operating system image entries by building `softwarerepository.OperatingSystemFile` objects. These image entries are intended for the later operating system installation workflow.

The normal user-facing inputs live in `group_vars/all.yml`:

```yaml
intersight_software_repository_catalog_name: "user-catalog"
intersight_software_repository_file_location: "https://your-repository/path/to/os-image.iso"
intersight_software_repository_operating_system_files:
  - name: "auto-vast-os-image"
    vendor: "Rocky Linux"
    version: "Rocky Linux 8.6"
```

Normal user inputs are:

- `intersight_software_repository_catalog_name`
- `name`
- `vendor`
- `version`
- `intersight_software_repository_file_location`
- optional `source_username` and `source_password`

`catalog_moid` remains available as an advanced fallback, but most users should use the catalog name.

Build or update the software repository OS image entry with:

```bash
cd "$REPO_HOME"
export INTERSIGHT_API_ENDPOINT="https://intersight.com"
ANSIBLE_LOCAL_TEMP=/tmp ANSIBLE_REMOTE_TEMP=/tmp ansible-playbook playbooks/build_software_repository.yml   -e intersight_apply_changes=true   -e intersight_organization=default
```

Expected result:

- Creates or updates the OS image entry in the selected software repository catalog
- Stores the image URL as the Intersight file location (`LocationLink`)
- Makes the image available for the later OS installation workflow

## Quick test

Use this path first when you want to validate the repository with the default organization before changing any inputs.

1. Build the policies and template in `default`
2. Derive one profile from the template

```bash
cd "$REPO_HOME"
export INTERSIGHT_API_ENDPOINT="https://intersight.com"

ANSIBLE_LOCAL_TEMP=/tmp ANSIBLE_REMOTE_TEMP=/tmp ansible-playbook playbooks/build_standalone_template.yml \
  -e intersight_apply_changes=true \
  -e intersight_organization=default \
  -e intersight_create_organization_if_missing=false \
  -e intersight_include_default_organization=false

ANSIBLE_LOCAL_TEMP=/tmp ANSIBLE_REMOTE_TEMP=/tmp ansible-playbook playbooks/configure_server_profiles.yml \
  -e intersight_apply_changes=true \
  -e intersight_organization=default \
  -e intersight_number_of_profiles=1
```

Expected result:

- policies created in `default`
- `auto-vast-template` created in `default`
- one derived profile created from that template

After that, users can change the variables in `group_vars/all.yml` or pass overrides on the command line.


## Notes

- Use the generic base endpoint `https://intersight.com`. The playbooks append `/api/v1` automatically.
- The playbooks are designed to be reusable across customer environments by changing variables rather than task logic
- Prefix variables let you separate automation-managed objects from manually created ones
