import argparse
import json
from pathlib import Path

from elder_indicators.config import load_config
from elder_indicators.signals import build_triple_screen_signals
from .provider import load_cached


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay cached A-share bars through the signal engine")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--signals-output", type=Path)
    args = parser.parse_args()

    config = load_config()
    bundle = load_cached(
        args.symbol,
        Path(__file__).resolve().parents[1] / config["market"]["cache"]["directory"],
    )
    weekly, daily, intraday = bundle.signal_frames(config["market"])
    signals = build_triple_screen_signals(
        weekly,
        daily,
        intraday,
        symbol=args.symbol,
        params=config["params"],
        market=config["market"],
    )
    output_path = args.signals_output or (
        Path(__file__).resolve().parents[1]
        / config["market"]["cache"]["directory"]
        / f"{args.symbol.replace('.', '_')}_signals.csv"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    signals.to_csv(output_path, index=False)
    print(
        json.dumps(
            {
                "symbol": args.symbol,
                "cached_provider": bundle.metadata["provider"],
                "signal_rows": len(signals),
                "signals_output": str(output_path),
                "source_page_values": sorted(signals["source_page"].dropna().unique().tolist()),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
