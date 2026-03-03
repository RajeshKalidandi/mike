"""Configuration CLI commands for Mike."""

import json
from pathlib import Path
from typing import Optional

import click

from mike.config.loader import ConfigLoader
from mike.config.profiles import ProfileManager
from mike.config.settings import Settings
from mike.config.validation import ConfigValidator


def get_config_group() -> click.Group:
    """Get the config CLI group."""

    @click.group(name="config")
    def config():
        """Manage configuration."""
        pass

    @config.command(name="init")
    @click.option(
        "--global",
        "global_",
        is_flag=True,
        help="Create global config in ~/.mike/",
    )
    @click.option(
        "--local",
        "local_",
        is_flag=True,
        help="Create local config in ./.mike/",
    )
    @click.option(
        "--force",
        "-f",
        is_flag=True,
        help="Overwrite existing config",
    )
    @click.pass_context
    def config_init(
        ctx: click.Context, global_: bool, local_: bool, force: bool
    ) -> None:
        """Create default configuration file."""
        loader = ConfigLoader()

        # Default to global if neither specified
        if not global_ and not local_:
            global_ = True

        created = []

        if global_:
            try:
                path = loader.create_default_config(
                    loader.user_config_dir,
                    exist_ok=force,
                )
                created.append(("Global", path))
            except FileExistsError:
                click.echo(
                    f"Global config already exists: {loader.user_config_dir}/config.yaml"
                )
                click.echo("Use --force to overwrite")
                return

        if local_:
            try:
                path = loader.create_default_config(
                    loader.project_config_dir,
                    exist_ok=force,
                )
                created.append(("Local", path))
            except FileExistsError:
                click.echo(
                    f"Local config already exists: {loader.project_config_dir}/config.yaml"
                )
                click.echo("Use --force to overwrite")
                return

        for name, path in created:
            click.echo(f"Created {name.lower()} config: {path}")

    @config.command(name="show")
    @click.option(
        "--format",
        "format_",
        type=click.Choice(["yaml", "json", "table"]),
        default="table",
        help="Output format",
    )
    @click.option(
        "--mask-secrets",
        is_flag=True,
        default=True,
        help="Mask sensitive values",
    )
    @click.option(
        "--profile",
        "-p",
        help="Show config for specific profile",
    )
    @click.pass_context
    def config_show(
        ctx: click.Context, format_: str, mask_secrets: bool, profile: Optional[str]
    ) -> None:
        """Display current configuration."""
        try:
            settings = ConfigLoader().load(profile=profile)
        except Exception as e:
            click.echo(f"Error loading config: {e}", err=True)
            raise click.Exit(1)

        if format_ == "yaml":
            try:
                click.echo(settings.to_yaml(mask_secrets=mask_secrets))
            except ImportError:
                click.echo("PyYAML not installed, falling back to JSON")
                click.echo(settings.to_json(mask_secrets=mask_secrets))
        elif format_ == "json":
            click.echo(settings.to_json(mask_secrets=mask_secrets))
        else:  # table
            _print_config_table(settings)

    def _print_config_table(settings: Settings) -> None:
        """Print configuration as formatted table."""
        click.echo()
        click.echo("=" * 60)
        click.echo("Mike Configuration")
        click.echo("=" * 60)

        if settings.profile:
            click.echo(f"\nActive Profile: {settings.profile}")

        # Database
        click.echo("\n[Database]")
        click.echo(f"  Path: {settings.database.path}")
        click.echo(f"  Pool Size: {settings.database.pool_size}")
        click.echo(f"  Timeout: {settings.database.timeout}s")

        # LLM
        click.echo("\n[LLM]")
        click.echo(f"  Provider: {settings.llm.provider}")
        click.echo(f"  Model: {settings.llm.model}")
        click.echo(f"  Temperature: {settings.llm.temperature}")
        click.echo(f"  Max Tokens: {settings.llm.max_tokens}")
        click.echo(f"  Context Window: {settings.llm.context_window}")

        # Embeddings
        click.echo("\n[Embeddings]")
        click.echo(f"  Provider: {settings.embeddings.provider}")
        click.echo(f"  Model: {settings.embeddings.model}")
        click.echo(f"  Dimensions: {settings.embeddings.dimensions}")
        click.echo(f"  Batch Size: {settings.embeddings.batch_size}")

        # Agents
        click.echo("\n[Agents]")
        click.echo(f"  Temperature: {settings.agents.temperature}")
        click.echo(f"  Max Tokens: {settings.agents.max_tokens}")
        click.echo(f"  Parallel: {settings.agents.parallel_agents}")
        click.echo(f"  Min Confidence: {settings.agents.thresholds.min_confidence}")

        # Scanner
        click.echo("\n[Scanner]")
        click.echo(
            f"  Max File Size: {settings.scanner.max_file_size / 1024 / 1024:.1f} MB"
        )
        click.echo(f"  Max Files: {settings.scanner.max_files}")
        click.echo(
            f"  Ignore Patterns: {len(settings.scanner.ignore_patterns)} patterns"
        )

        # Paths
        click.echo("\n[Paths]")
        click.echo(f"  Cache: {settings.paths.cache_dir}")
        click.echo(f"  Output: {settings.paths.output_dir}")
        click.echo(f"  Vector Store: {settings.paths.vector_store_dir}")

        # Logging
        click.echo("\n[Logging]")
        click.echo(f"  Level: {settings.logging.level.value}")
        if settings.logging.file:
            click.echo(f"  File: {settings.logging.file}")

        click.echo("\n" + "=" * 60)

    @config.command(name="validate")
    @click.option(
        "--check-models",
        is_flag=True,
        default=True,
        help="Check model availability",
    )
    @click.option(
        "--profile",
        "-p",
        help="Validate specific profile",
    )
    @click.pass_context
    def config_validate(
        ctx: click.Context, check_models: bool, profile: Optional[str]
    ) -> None:
        """Validate current configuration."""
        try:
            settings = ConfigLoader().load(profile=profile)
        except Exception as e:
            click.echo(f"Error loading config: {e}", err=True)
            raise click.Exit(1)

        click.echo("Validating configuration...")
        click.echo()

        validator = ConfigValidator(check_models=check_models)
        result = validator.validate(settings)

        # Also check dependencies
        dep_result = validator.check_dependencies()
        result.merge(dep_result)

        # Print results
        if result.is_valid and not result.warnings:
            click.echo("✓ Configuration is valid")
        elif result.is_valid:
            click.echo("✓ Configuration is valid (with warnings)")
        else:
            click.echo("✗ Configuration has errors")

        if result.errors:
            click.echo(f"\nErrors ({len(result.errors)}):")
            for error in result.errors:
                click.echo(f"  ✗ {error.field}: {error.message}")

        if result.warnings:
            click.echo(f"\nWarnings ({len(result.warnings)}):")
            for warning in result.warnings:
                click.echo(f"  ⚠ {warning.field}: {warning.message}")

        if not result.is_valid:
            raise click.Exit(1)

    @config.command(name="set")
    @click.argument("key")
    @click.argument("value")
    @click.option(
        "--global",
        "global_",
        is_flag=True,
        help="Set in global config",
    )
    @click.option(
        "--local",
        "local_",
        is_flag=True,
        help="Set in local config",
    )
    @click.pass_context
    def config_set(
        ctx: click.Context, key: str, value: str, global_: bool, local_: bool
    ) -> None:
        """Set a configuration value.

        KEY should be in dot notation (e.g., llm.model, database.path)
        """
        # Determine which config file to modify
        if global_ and local_:
            click.echo("Error: Cannot use both --global and --local", err=True)
            raise click.Exit(1)

        loader = ConfigLoader()

        if local_:
            config_dir = loader.project_config_dir
        else:
            config_dir = loader.user_config_dir

        # Load existing config or create new
        config_file = config_dir / "config.yaml"
        if config_file.exists():
            try:
                import yaml

                config = yaml.safe_load(config_file.read_text()) or {}
            except ImportError:
                click.echo("PyYAML required for config editing", err=True)
                raise click.Exit(1)
        else:
            config = {}
            config_dir.mkdir(parents=True, exist_ok=True)

        # Parse key into nested structure
        keys = key.split(".")
        current = config
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]

        # Convert value to appropriate type
        typed_value = _convert_set_value(value)
        current[keys[-1]] = typed_value

        # Save config
        try:
            import yaml

            config_file.write_text(
                yaml.dump(config, default_flow_style=False, sort_keys=False)
            )
        except ImportError:
            click.echo("PyYAML required for config editing", err=True)
            raise click.Exit(1)

        click.echo(f"Set {key} = {typed_value}")

    def _convert_set_value(value: str) -> any:
        """Convert a string value to appropriate type."""
        # Boolean
        if value.lower() in ("true", "yes"):
            return True
        if value.lower() in ("false", "no"):
            return False

        # Null
        if value.lower() in ("null", "none", "~"):
            return None

        # Number
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            pass

        # String (default)
        return value

    @config.command(name="get")
    @click.argument("key")
    @click.option(
        "--profile",
        "-p",
        help="Get value for specific profile",
    )
    @click.pass_context
    def config_get(ctx: click.Context, key: str, profile: Optional[str]) -> None:
        """Get a configuration value.

        KEY should be in dot notation (e.g., llm.model, database.path)
        """
        try:
            settings = ConfigLoader().load(profile=profile)
        except Exception as e:
            click.echo(f"Error loading config: {e}", err=True)
            raise click.Exit(1)

        # Navigate to value
        keys = key.split(".")
        current = settings

        try:
            for k in keys:
                if hasattr(current, k):
                    current = getattr(current, k)
                elif isinstance(current, dict) and k in current:
                    current = current[k]
                else:
                    click.echo(f"Error: Key not found: {key}", err=True)
                    raise click.Exit(1)

            click.echo(current)
        except click.Exit:
            raise
        except Exception as e:
            click.echo(f"Error accessing {key}: {e}", err=True)
            raise click.Exit(1)

    @config.command(name="profiles")
    @click.pass_context
    def config_profiles(ctx: click.Context) -> None:
        """List available configuration profiles."""
        manager = ProfileManager()

        profiles = manager.list_profiles()

        click.echo("\nAvailable Profiles:")
        click.echo("=" * 60)

        for profile in profiles:
            builtin = (
                "(built-in)" if profile.name in manager.BUILTIN_PROFILES else "(custom)"
            )
            click.echo(f"\n  {profile.name} {builtin}")
            click.echo(f"    {profile.description}")

        click.echo("\n" + "=" * 60)
        click.echo("\nUse: mike config use-profile <name>")

    @config.command(name="use-profile")
    @click.argument("name")
    @click.option(
        "--global",
        "global_",
        is_flag=True,
        help="Set in global config",
    )
    @click.option(
        "--local",
        "local_",
        is_flag=True,
        help="Set in local config",
    )
    @click.pass_context
    def config_use_profile(
        ctx: click.Context, name: str, global_: bool, local_: bool
    ) -> None:
        """Set the active configuration profile."""
        # Determine which config file to modify
        if global_ and local_:
            click.echo("Error: Cannot use both --global and --local", err=True)
            raise click.Exit(1)

        loader = ConfigLoader()

        if local_:
            config_dir = loader.project_config_dir
        else:
            config_dir = loader.user_config_dir

        # Validate profile exists
        manager = ProfileManager()
        if not manager.has_profile(name):
            click.echo(f"Error: Profile not found: {name}", err=True)
            click.echo("\nAvailable profiles:")
            for profile in manager.list_profiles():
                click.echo(f"  - {profile.name}")
            raise click.Exit(1)

        # Load existing config or create new
        config_file = config_dir / "config.yaml"
        if config_file.exists():
            try:
                import yaml

                config = yaml.safe_load(config_file.read_text()) or {}
            except ImportError:
                click.echo("PyYAML required for config editing", err=True)
                raise click.Exit(1)
        else:
            config = {}
            config_dir.mkdir(parents=True, exist_ok=True)

        # Set profile
        config["profile"] = name

        # Save config
        try:
            import yaml

            config_file.write_text(
                yaml.dump(config, default_flow_style=False, sort_keys=False)
            )
        except ImportError:
            click.echo("PyYAML required for config editing", err=True)
            raise click.Exit(1)

        click.echo(f"Set active profile to: {name}")

    @config.command(name="schema")
    @click.option(
        "--output",
        "-o",
        type=click.Path(),
        help="Write schema to file",
    )
    @click.pass_context
    def config_schema(ctx: click.Context, output: Optional[str]) -> None:
        """Generate JSON schema for configuration."""
        from mike.config.settings import generate_schema

        schema = generate_schema()

        if output:
            Path(output).write_text(schema)
            click.echo(f"Schema written to: {output}")
        else:
            click.echo(schema)

    return config
