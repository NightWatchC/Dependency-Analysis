import argparse


def parse_args():
    parser = argparse.ArgumentParser(
        description="A tiny argparse learning demo."
    )

    # 位置参数（必填）
    parser.add_argument("project", help="Project name, e.g. MyTool")

    # 可选参数（带默认值）
    parser.add_argument("--name", default="Alice", help="Your name")
    parser.add_argument("--age", type=int, default=18, help="Your age")
    parser.add_argument("--score", type=float, default=60.0, help="Your score")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose mode")

    return parser.parse_args()


def main():
    args = parse_args()

    print("=== Raw Parsed Args ===")
    print(args)

    print("\n=== Use Parameters ===")
    print(f"Project: {args.project}")
    print(f"Name: {args.name}")
    print(f"Age next year: {args.age + 1}")
    print(f"Score + 5: {args.score + 5}")

    if args.verbose:
        print("\n[VERBOSE] Detailed summary:")
        print(f"- project: {args.project}")
        print(f"- name: {args.name}")
        print(f"- age type: {type(args.age).__name__}")
        print(f"- score type: {type(args.score).__name__}")


if __name__ == "__main__":
    main()
