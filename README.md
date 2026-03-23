# VAST_Intersight_Automation

`VAST_Intersight_Automation` automates a standalone Cisco Intersight build in four stages:

1. Organizations
2. Policies
3. Server profile templates
4. Server profiles derived from templates

The automation is driven from `group_vars/all.yml`.

## Repository layout

- `playbooks/test_org.yml`: create or validate an organization only
- `playbooks/build_standalone_template.yml`: create policies and template
- `playbooks/configure_server_profiles.yml`: derive server profiles from a template
- `roles/intersight_organization/`: organization create and default-org sharing
- `roles/intersight_policy_catalog/`: policy creation
- `roles/intersight_server_profile_templates/`: template creation
- `roles/intersight_server_profiles/`: server profile derive flow
- `group_vars/all.yml`: main user inputs
- `requirements.yml`: required Ansible collection

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
- `intersight_number_of_profiles`

`intersight_apply_changes` is the safety gate. Keep it `false` until you want to write to Intersight.

Use `intersight_organization` as the normal user input. `intersight_organization_moid` is an advanced override for cases where you want to target a specific organization object directly and skip name-based lookup. Most users should leave it empty.

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

## 1. Organizations

The organization role does the following:

- looks up the target organization by name
- creates it if it does not exist and creation is allowed
- refreshes and reapplies the org metadata after create
- optionally shares resources from the `default` organization into the target org

The share toggle is:

- `intersight_include_default_organization: true`

That creates the Intersight sharing rule so the target org can consume shared resources from `default`.

Test only the organization flow:

```bash
cd "$REPO_HOME"
export INTERSIGHT_API_ENDPOINT="https://intersight.com"
ANSIBLE_LOCAL_TEMP=/tmp ANSIBLE_REMOTE_TEMP=/tmp ansible-playbook playbooks/test_org.yml \
  -e intersight_organization=create-new-org \
  -e intersight_create_organization_if_missing=true \
  -e intersight_include_default_organization=true
```

## 2. Policies

The policy catalog currently builds these standalone policies:

- BIOS
- Boot Order
- Power
- IPMI over LAN
- Local User
- Serial over LAN
- Virtual KVM
- Storage

Policy names are driven by `intersight_policy_name_prefix`. By default they are created as:

- `auto-vast-bios`
- `auto-vast-bootorder`
- `auto-vast-power`
- `auto-vast-ipmi`
- `auto-vast-localuser`
- `auto-vast-sol`
- `auto-vast-vkvm`
- `auto-vast-storage`

These policy definitions live in `group_vars/all.yml` under `intersight_policy_catalog`.

Build policies together with the template:

```bash
cd "$REPO_HOME"
export INTERSIGHT_API_ENDPOINT="https://intersight.com"
ANSIBLE_LOCAL_TEMP=/tmp ANSIBLE_REMOTE_TEMP=/tmp ansible-playbook playbooks/build_standalone_template.yml \
  -e intersight_apply_changes=true \
  -e intersight_organization=default \
  -e intersight_create_organization_if_missing=false \
  -e intersight_include_default_organization=false
```

You can also run the targeted policy test playbooks individually:

- `playbooks/test_auto_bios.yml`
- `playbooks/test_auto_bootorder.yml`
- `playbooks/test_auto_power.yml`
- `playbooks/test_auto_storage.yml`
- `playbooks/test_auto_sol.yml`
- `playbooks/test_auto_vkvm.yml`
- `playbooks/test_auto_ipmi.yml`
- `playbooks/test_auto_local_user.yml`

## 3. Templates

The server profile template role:

- resolves the policy MOIDs in the target org
- attaches the policy bucket to the template
- creates or updates the standalone template

The current template input is in `group_vars/all.yml` under `intersight_server_profile_templates`.

By default the template name is:

- `auto-vast-template`

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

## 4. Profiles

The server profile flow derives profiles from an existing template by using the same `bulk.MoCloner` flow used by the Intersight UI.

Current user-facing inputs:

- `template_name`
- `base_name`
- `description`
- `organization`
- `start_index`
- `auto_start_index`
- `intersight_number_of_profiles`

The top-level count input is:

```yaml
intersight_number_of_profiles: 1
```

If `auto_start_index: false`, the derive flow starts at `start_index`.

If `auto_start_index: true`, the derive flow:

- reads existing server profiles in the target org
- finds names matching `base_name_DERIVED-<number>`
- starts at the next available suffix

Example server profile inputs in `group_vars/all.yml`:

```yaml
intersight_number_of_profiles: 1

intersight_server_profiles:
  - template_name: "{{ intersight_template_name_prefix }}vast-template"
    base_name: "{{ intersight_template_name_prefix }}vast-template"
    start_index: 1
    auto_start_index: true
    description: "derive profiles from AUTO"
    organization: "{{ intersight_organization }}"
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

With the example above, the created profile names will look like:

- `auto-vast-template_DERIVED-1`
- `auto-vast-template_DERIVED-2`
- `auto-vast-template_DERIVED-3`

depending on `intersight_number_of_profiles` and the start-index settings.

## Recommended workflow

1. Configure credentials and endpoint
2. Set organization inputs
3. Build policies and template with `playbooks/build_standalone_template.yml`
4. Verify the template in Intersight
5. Set profile inputs
6. Derive server profiles with `playbooks/configure_server_profiles.yml`

## Notes

- Use the generic base endpoint `https://intersight.com`. The playbooks append `/api/v1` automatically.
- The playbooks are designed to be reusable across customer environments by changing variables rather than task logic
- Prefix variables let you separate automation-managed objects from manually created ones
