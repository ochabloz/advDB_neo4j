"""
Script that import a DBLP database to a neo4j instance
"""
import sys, os, argparse, json, time, datetime
import tqdm


def process_line(line, db_instance):
    parsed_line = json.loads(line)


if __name__ == "__main__":
    SCRIPT_DESCRIPTION = "Import dblp data in the form of a JSON file into a neo4j database"
    cmdline_parser = argparse.ArgumentParser(description=SCRIPT_DESCRIPTION)

    cmdline_parser.add_argument("--db_host", default=os.environ.get("NEO4J_HOST", "localhost"))
    cmdline_parser.add_argument("--db_port", default=os.environ.get("NEO4J_PORT", "9490"), type=int)
    cmdline_parser.add_argument("--db_user", default=os.environ.get("NEO4J_USER", "neo4j"))
    cmdline_parser.add_argument("--db_pswd", default=os.environ.get("NEO4J_PSWD", "neo4j"))
    cmdline_parser.add_argument(
        "-i", "--input", help="JSON file to import, '-' to read from STDIN. default: '-'", default="-"
    )
    cmdline_parser.add_argument("--stop_it", type=int, help="stop after n lines", default=os.environ.get("STOP_IT"))

    args = cmdline_parser.parse_args()

    total_lines = None
    if args.input != "-":
        with open(args.input, "rb") as f:
            for total_lines, _ in enumerate(f, start=1):
                pass

        stream_input = open(args.input, "rb")

    else:
        stream_input = sys.stdin

    iterator = tqdm.tqdm(stream_input, total=total_lines, unit="line")
    for l in iterator:
        process_line(l, db_instance=None)
        if args.stop_it is not None and iterator.n > args.stop_it:
            break

    iterator.close()
    if iterator.n == 0:
        sys.exit()
    total_t = datetime.timedelta(seconds=time.time() - iterator.start_t)
    print(f"Number of entries processed: {iterator.n}, total time: {str(total_t)}")
    print(f"Average: {total_t.total_seconds()/iterator.n:.05f}[s] per line")

