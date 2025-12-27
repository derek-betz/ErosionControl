# EC Agent Usage Guide

This guide provides detailed examples and usage scenarios for the EC Agent.

## Table of Contents

- [Installation](#installation)
- [Basic Usage](#basic-usage)
- [Web UI](#web-ui)
- [Desktop UI](#desktop-ui)
- [Input File Format](#input-file-format)
- [Output Format](#output-format)
- [Custom Rules](#custom-rules)
- [LLM Enhancement](#llm-enhancement)
- [Common Scenarios](#common-scenarios)

## Installation

```bash
# Install from source
git clone https://github.com/derek-betz/ErosionControl.git
cd ErosionControl

# Windows bootstrap (installs Python, dev deps, and runs tests)
powershell -ExecutionPolicy Bypass -File scripts/bootstrap.ps1

pip install -e .

# Or with LLM support
pip install -e ".[llm]"
```

### Download BidTabsData (optional for training samples)

```bash
export BIDTABSDATA_VERSION=<release-tag>
# Optional overrides:
# BIDTABSDATA_REPO=derek-betz/BidTabsData
# BIDTABSDATA_HOST=github.company.com
# BIDTABSDATA_OUT_DIR=data-sample/BidTabsData
# BIDTABSDATA_URL=https://artifacts.company.com/BidTabsData-v0.1.0.zip
# BIDTABSDATA_ARCHIVE=\\server\share\BidTabsData-v0.1.0.zip
# BIDTABSDATA_CACHE_DIR=~/.cache/ec-agent/bidtabsdata
python scripts/fetch_bidtabsdata.py
```

`BIDTABSDATA_VERSION` must match a GitHub Release tag in `derek-betz/BidTabsData` and will download
`BidTabsData-${BIDTABSDATA_VERSION}.zip` into `data-sample/BidTabsData`
(`.bidtabsdata_version` is written with the tag). Override the repository or output directory with
`BIDTABSDATA_REPO` and `BIDTABSDATA_OUT_DIR` if needed.
If GitHub access is restricted, set `BIDTABSDATA_URL` to a reachable mirror or
`BIDTABSDATA_ARCHIVE` to a local zip. When `BIDTABSDATA_VERSION` is omitted, the script will infer
it from a `BidTabsData-<version>.zip` filename.

## Basic Usage

### Validate a Project File

Before processing, validate your project file:

```bash
ec-agent validate examples/highway_project.yaml
```

### Process a Project

Generate EC recommendations:

```bash
# Process and display results
ec-agent process examples/highway_project.yaml

# Save results to a file
ec-agent process examples/highway_project.yaml --output results.yaml

# Quiet mode (no console output)
ec-agent process examples/highway_project.yaml --output results.yaml --quiet
```

### Use Custom Rules

Apply jurisdiction-specific or custom rules:

```bash
ec-agent process my_project.yaml --rules my_custom_rules.yaml --output results.yaml
```

## Web UI

Run the local web interface:

```bash
ec-agent web
```

Open `http://127.0.0.1:8000` in your browser. Paste project YAML/JSON, add optional
custom rules, then run the analysis and download results.


## Desktop UI

Run the desktop interface:

```bash
ec-agent desktop
```

Use the tabs to paste project input and custom rules, then run analysis and save output.

## Input File Format

### Minimal Example (YAML)

```yaml
project_name: My Road Project
jurisdiction: State DOT
total_disturbed_acres: 3.5
predominant_soil: clay
predominant_slope: moderate
average_slope_percent: 15.0
```

### Comprehensive Example (YAML)

```yaml
project_name: Highway 101 Widening Project
jurisdiction: California DOT
total_disturbed_acres: 5.2
predominant_soil: clay
predominant_slope: moderate
average_slope_percent: 18.5

drainage_features:
  - id: INLET-001
    type: inlet
    location: Station 10+50, North side
    drainage_area_acres: 2.3
    additional_properties:
      inlet_type: curb_inlet
      grate_size: 24x36

phases:
  - phase_id: PHASE-1
    name: Clearing and Grubbing
    duration_days: 15
    disturbed_acres: 5.2
    description: Initial site preparation

metadata:
  project_engineer: Jane Smith, PE
  contractor: ABC Construction Inc.
  estimated_start_date: "2024-03-01"
```

### JSON Format

The same structure works in JSON:

```json
{
  "project_name": "My Road Project",
  "jurisdiction": "City DOT",
  "total_disturbed_acres": 2.5,
  "predominant_soil": "sand",
  "predominant_slope": "gentle",
  "average_slope_percent": 8.0,
  "drainage_features": [],
  "phases": []
}
```

## Output Format

### Example Output

```yaml
project_name: Highway 101 Widening Project
timestamp: '2024-01-15T10:30:00'

temporary_practices:
  - practice_type: silt_fence
    is_temporary: true
    quantity: 1040.0
    unit: LF
    location: Perimeter of disturbed area
    rule_id: SILT_FENCE_001
    rule_source: EPA NPDES CGP
    justification: Perimeter sediment control
    notes: ''

permanent_practices:
  - practice_type: permanent_seeding
    is_temporary: false
    quantity: 5.2
    unit: AC
    location: All disturbed areas
    rule_id: PERM_SEED_001
    rule_source: State DOT Standard Specifications
    justification: Permanent vegetation establishment

pay_items:
  - item_number: EC-001
    description: Silt Fence, Type A
    quantity: 1040.0
    unit: LF
    estimated_unit_cost: 3.5
    ec_practice_ref: silt_fence_SILT_FENCE_001
    rule_id: SILT_FENCE_001
    rule_source: EPA NPDES CGP

summary:
  total_temporary_practices: 4
  total_permanent_practices: 1
  total_pay_items: 5
  total_estimated_cost: 8490.0
```

## Custom Rules

### Creating Custom Rules

Create a YAML file with custom rules:

```yaml
rules:
  - id: LOCAL_RULE_001
    name: Local Jurisdiction Special Rule
    source: City Stormwater Management Manual
    priority: 10  # Lower = higher priority
    
    conditions:
      - field: total_disturbed_acres
        operator: gte
        value: 1.0
      - field: predominant_soil
        operator: in
        value: [sand, silt]
    
    action:
      practice_type: mulch
      is_temporary: true
      quantity_formula: total_disturbed_acres * 1000
      unit: SY
      location_template: All exposed soil areas
      justification: Local requirement for sandy/silty soils
      pay_item_number: EC-020
      pay_item_description: Straw Mulch
      estimated_unit_cost: 1.50
    
    notes: Apply 2-inch depth minimum
```

### Rule Conditions

Available operators:
- `eq`: Equal to
- `ne`: Not equal to
- `gt`: Greater than
- `gte`: Greater than or equal to
- `lt`: Less than
- `lte`: Less than or equal to
- `in`: Value is in list
- `contains`: String contains substring

Available fields:
- `total_disturbed_acres`
- `predominant_soil` (clay, silt, sand, gravel, loam, bedrock)
- `predominant_slope` (flat, gentle, moderate, steep, very_steep)
- `average_slope_percent`
- `has_drainage_features` (boolean)
- `drainage_feature_count`

### Quantity Formulas

Use simple Python expressions:
```yaml
quantity_formula: total_disturbed_acres * 200
quantity_formula: drainage_feature_count * 2
quantity_formula: total_disturbed_acres * 43560 / 9  # Convert acres to SY
```

## LLM Enhancement

Enable LLM-powered insights:

```bash
# Set API key
export OPENAI_API_KEY=your-api-key

# Process with LLM enhancement
ec-agent process my_project.yaml --llm --output results.yaml
```

LLM enhancement provides:
- Overall assessment of recommended practices
- Additional considerations
- Risk identification
- Sequencing recommendations

You can also set `OPENAI_API_KEY_FILE` to a key file path or place the key in
`API_KEY/API_KEY.txt` in your working directory.

## Common Scenarios

### Scenario 1: Small Residential Project

```yaml
project_name: Residential Street
jurisdiction: City Public Works
total_disturbed_acres: 0.8
predominant_soil: loam
predominant_slope: flat
average_slope_percent: 3.0
```

Expected practices:
- Silt fence perimeter (160 LF)
- Construction entrance (1 EA)
- Permanent seeding (0.8 AC)

### Scenario 2: Highway with Steep Slopes

```yaml
project_name: Mountain Highway
jurisdiction: State DOT
total_disturbed_acres: 8.0
predominant_soil: clay
predominant_slope: steep
average_slope_percent: 35.0
drainage_features:
  - id: CULVERT-1
    type: culvert
    location: Station 50+00
    drainage_area_acres: 10.0
```

Expected practices:
- Silt fence perimeter
- Erosion control blanket (steep slopes)
- Inlet/culvert protection
- Construction entrance
- Permanent seeding

### Scenario 3: Phased Construction

```yaml
project_name: Multi-Phase Development
jurisdiction: County DOT
total_disturbed_acres: 15.0
predominant_soil: sand
predominant_slope: gentle
average_slope_percent: 8.0

phases:
  - phase_id: P1
    name: Phase 1 - South Section
    duration_days: 45
    disturbed_acres: 5.0
  
  - phase_id: P2
    name: Phase 2 - North Section
    duration_days: 45
    disturbed_acres: 10.0
```

## Troubleshooting

### Issue: "Validation failed: field required"

**Solution:** Ensure all required fields are present in your input file:
- project_name
- jurisdiction
- total_disturbed_acres
- predominant_soil
- predominant_slope
- average_slope_percent

### Issue: "No rules matched"

**Solution:** Check that your project characteristics meet the conditions of at least one rule. You may need to create custom rules for your specific scenario.

### Issue: "Cannot represent an object" (YAML error)

**Solution:** This is handled automatically by the tool using `model_dump(mode="json")`. If you see this, please report it as a bug.

## Best Practices

1. **Start Small**: Begin with a minimal project file and add details as needed
2. **Validate First**: Always validate your input file before processing
3. **Use Consistent Units**: Acres for areas, linear feet (LF) for lengths
4. **Document Metadata**: Include project engineer, permit numbers, dates
5. **Custom Rules**: Create jurisdiction-specific rules files for reuse
6. **Version Control**: Keep your project files and custom rules in version control

## Getting Help

- Check the [README](README.md) for installation and quick start
- See [CONTRIBUTING](CONTRIBUTING.md) for development guidelines
- Open an issue on GitHub for bugs or feature requests
- Use `ec-agent --help` for CLI documentation
