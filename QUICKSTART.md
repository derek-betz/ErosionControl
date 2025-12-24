# EC Agent Quick Start

Get started with EC Agent in 5 minutes!

## 1. Install

```bash
pip install -e .
```

## 2. Launch the Web UI (Optional)

```bash
ec-agent web
```

Open `http://127.0.0.1:8000` in your browser.

## 3. Launch the Desktop UI (Optional)

```bash
ec-agent desktop
```

## 4. Validate an Example

```bash
ec-agent validate examples/highway_project.yaml
```

## 5. Process a Project

```bash
ec-agent process examples/highway_project.yaml
```

You'll see output like:

```
EC Agent Results for: Highway 101 Widening Project
Generated: 2024-01-15T10:30:00

               Summary                
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┓
┃ Metric                    ┃ Value  ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━┩
│ Total Temporary Practices │ 3      │
│ Total Permanent Practices │ 1      │
│ Total Pay Items           │ 4      │
│ Total Estimated Cost      │ 8490.0 │
└───────────────────────────┴────────┘
```

## 6. Save Results

```bash
ec-agent process examples/highway_project.yaml --output my_results.yaml
```

## 7. Create Your Own Project

Create `my_project.yaml`:

```yaml
project_name: My Road Project
jurisdiction: State DOT
total_disturbed_acres: 3.5
predominant_soil: clay
predominant_slope: moderate
average_slope_percent: 15.0
```

Then process it:

```bash
ec-agent process my_project.yaml --output results.yaml
```

## Next Steps

- Read the [USAGE.md](USAGE.md) for detailed examples
- Check [README.md](README.md) for full documentation
- See [CONTRIBUTING.md](CONTRIBUTING.md) to add features
- Explore `examples/` for more project templates

## Need Help?

- Run `ec-agent --help` for CLI documentation
- Open an issue on GitHub
- Check the documentation files

Happy engineering! 🚧
