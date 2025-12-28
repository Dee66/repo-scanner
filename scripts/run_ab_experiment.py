#!/usr/bin/env python3
"""
A/B Experiment Runner
Command-line interface for running A/B experiments
"""

import argparse
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from core.ab_testing.framework import ABTestingFramework, ExperimentVariant, VariantType


def create_experiment(args):
    """Create a new A/B experiment"""
    framework = ABTestingFramework()

    # Load control variant from file or create default
    if args.control_config:
        with open(args.control_config, 'r') as f:
            control_config = json.load(f)
    else:
        control_config = {}

    control = ExperimentVariant(
        name="control",
        type=VariantType.CONTROL,
        config=control_config,
        description="Baseline configuration"
    )

    # Load treatment variants
    treatments = []
    if args.treatment_configs:
        for i, config_file in enumerate(args.treatment_configs):
            with open(config_file, 'r') as f:
                config = json.load(f)
            treatment = ExperimentVariant(
                name=f"treatment_{i+1}",
                type=VariantType.TREATMENT,
                config=config,
                description=f"Treatment variant {i+1}"
            )
            treatments.append(treatment)

    # Load test repositories
    test_repos = []
    if args.repositories_file:
        with open(args.repositories_file, 'r') as f:
            test_repos = [line.strip() for line in f if line.strip()]
    elif args.repositories:
        test_repos = args.repositories

    experiment_id = framework.create_experiment(
        name=args.name,
        description=args.description,
        control_variant=control,
        treatment_variants=treatments,
        test_repositories=test_repos
    )

    print(f"✅ Created experiment: {experiment_id}")
    return experiment_id


def run_experiment(args):
    """Run an existing experiment"""
    framework = ABTestingFramework()

    print(f"🚀 Running experiment: {args.experiment_id}")
    success = framework.run_experiment(args.experiment_id)

    if success:
        print("✅ Experiment completed successfully")
        # Generate report
        report = framework.get_experiment_report(args.experiment_id)
        print(f"📊 Results saved to: experiments/{args.experiment_id}.json")
    else:
        print("❌ Experiment failed")
        sys.exit(1)


def show_report(args):
    """Show experiment report"""
    framework = ABTestingFramework()

    try:
        report = framework.get_experiment_report(args.experiment_id)
        print(f"📋 Experiment Report: {report['name']}")
        print(f"📝 Description: {report['description']}")
        print(f"📊 Status: {report['status']}")

        if report['status'] == 'completed':
            print(f"🏆 Results: {len(report['results'])} trials completed")

            # Show statistical analysis
            if report.get('analysis'):
                print("\n📈 Statistical Analysis:")
                for metric, analyses in report['analysis'].items():
                    print(f"\n  📊 Metric: {metric}")
                    for analysis in analyses:
                        sig = "✅" if analysis['significant'] else "❌"
                        print(f"    {sig} {analysis['variant_a']} vs {analysis['variant_b']}:")
                        print(f"      Mean A: {analysis['mean_a']:.3f}, Mean B: {analysis['mean_b']:.3f}")
                        print(f"      P-value: {analysis['p_value']:.4f}, Effect size: {analysis['effect_size']:.3f}")
                        if analysis['significant']:
                            print("      🎯 Statistically significant improvement!")
                        else:
                            print("      🤔 No significant difference detected")
        else:
            print("⏳ Experiment not yet completed")

    except ValueError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


def list_experiments(args):
    """List all experiments"""
    framework = ABTestingFramework()
    experiments = framework.list_experiments()

    if not experiments:
        print("📭 No experiments found")
        return

    print("📚 Available Experiments:")
    for exp in experiments:
        status_emoji = {
            'draft': '📝',
            'running': '🏃',
            'completed': '✅',
            'failed': '❌'
        }.get(exp['status'], '❓')

        print(f"  {status_emoji} {exp['id']}: {exp['name']} ({exp['status']})")


def main():
    parser = argparse.ArgumentParser(description="A/B Experiment Runner")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Create experiment
    create_parser = subparsers.add_parser('create', help='Create a new experiment')
    create_parser.add_argument('--name', required=True, help='Experiment name')
    create_parser.add_argument('--description', required=True, help='Experiment description')
    create_parser.add_argument('--control-config', help='JSON file with control configuration')
    create_parser.add_argument('--treatment-configs', nargs='+', help='JSON files with treatment configurations')
    create_parser.add_argument('--repositories', nargs='+', help='List of repository URLs to test')
    create_parser.add_argument('--repositories-file', help='File containing repository URLs (one per line)')

    # Run experiment
    run_parser = subparsers.add_parser('run', help='Run an experiment')
    run_parser.add_argument('experiment_id', help='Experiment ID to run')

    # Show report
    report_parser = subparsers.add_parser('report', help='Show experiment report')
    report_parser.add_argument('experiment_id', help='Experiment ID to report on')

    # List experiments
    list_parser = subparsers.add_parser('list', help='List all experiments')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == 'create':
        create_experiment(args)
    elif args.command == 'run':
        run_experiment(args)
    elif args.command == 'report':
        show_report(args)
    elif args.command == 'list':
        list_experiments(args)


if __name__ == '__main__':
    main()