"""Main module for sample project."""


def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


def main():
    """Main entry point."""
    result = add(1, 2)
    print(f"Result: {result}")


if __name__ == "__main__":
    main()
