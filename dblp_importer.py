"""
Script that import a DBLP database to a neo4j instance
"""
import sys, os, argparse, json, time, datetime
import tqdm
from fill_db import Consumer
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s::%(levelname)s::%(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


if __name__ == "__main__":
    SCRIPT_DESCRIPTION = "Import dblp data in the form of a JSON file into a neo4j database"
    cmdline_parser = argparse.ArgumentParser(description=SCRIPT_DESCRIPTION)

    cmdline_parser.add_argument("--tx_size", default=os.environ.get("DBLP_TX_SIZE", 1000), type=int)
    cmdline_parser.add_argument("--db_host", default=os.environ.get("DB_HOST", "localhost"))
    cmdline_parser.add_argument("--db_port", default=os.environ.get("DB_PORT", "9490"), type=int)
    cmdline_parser.add_argument("--db_user", default=os.environ.get("DB_USER", "neo4j"))
    cmdline_parser.add_argument("--db_pswd", default=os.environ.get("DB_PSWD", "neo4j_password"))
    cmdline_parser.add_argument(
        "-i",
        "--input",
        help="JSON file to import, '-' to read from STDIN. default: '-'",
        default="-",
    )
    cmdline_parser.add_argument(
        "--stop_it",
        type=int,
        help="stop after n lines",
        default=os.environ.get("STOP_IT"),
    )

    args = cmdline_parser.parse_args()
    logger.info(
        "Args: DB_HOST: %s, CREDS: %s/%s, TX_SIZE: %d",
        args.db_host,
        args.db_user,
        args.db_pswd,
        args.tx_size,
    )

    total_lines = None
    if args.input != "-":
        with open(args.input, "rb") as f:
            for total_lines, _ in enumerate(f, start=1):
                pass

        stream_input = open(args.input, "rb")
        total_lines = args.stop_it or total_lines

    else:
        stream_input = sys.stdin
        total_lines = args.stop_it or 5354309

    consumer = Consumer(
        f"neo4j://{args.db_host}:{args.db_port}",
        args.db_user,
        args.db_pswd,
        tx_limit=args.tx_size,
    )
    consumer.set_constraints()

    iterator = tqdm.tqdm(stream_input, total=total_lines, unit="line")
    for l in iterator:
        consumer.feed_line(l)
        if args.stop_it is not None and iterator.n > args.stop_it:
            break

    consumer.close()
    iterator.close()

    if iterator.n == 0:
        sys.exit()
    total_t = datetime.timedelta(seconds=time.time() - iterator.start_t)
    print(f"Number of entries processed: {iterator.n}, total time: {str(total_t)}")
    print(f"Average: {total_t.total_seconds()/iterator.n:.05f}[s] per line")
