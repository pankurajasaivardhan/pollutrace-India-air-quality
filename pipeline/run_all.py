"""Run the whole pipeline: python pipeline/run_all.py --raw-dir DATA --out OUT [--epochs N]"""
import argparse, json, os, platform, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common, forecast, anomalies, sources  # noqa: E402


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--raw-dir", default=os.environ.get("POLLUTRACE_RAW_DIR"))
    p.add_argument("--out", default="outputs")
    p.add_argument("--models", default=None, help="model dir (default OUT/models)")
    p.add_argument("--epochs", type=int, default=60)
    a = p.parse_args()
    if not a.raw_dir:
        sys.exit("pass --raw-dir or set POLLUTRACE_RAW_DIR")
    models = a.models or os.path.join(a.out, "models")
    t0 = time.time()
    cd = common.load_city_daily(a.raw_dir)
    os.makedirs(a.out, exist_ok=True)
    cd.to_csv(os.path.join(a.out, "city_daily.csv"), index=False)
    import tensorflow as tf
    info = {"python": platform.python_version(), "tensorflow": tf.__version__,
            "gpus": [d.name for d in tf.config.list_physical_devices("GPU")],
            "station_files_used": cd.attrs.get("n_station_files"), "city_days": len(cd),
            "seed": common.SEED, "seq_len": common.SEQ_LEN,
            "split": {"train": common.TRAIN_FRAC, "val": common.VAL_FRAC, "test": round(1 - common.TRAIN_FRAC - common.VAL_FRAC, 2)}}
    forecast.run_all(cd, models, a.out, a.epochs)
    anomalies.run_all(cd, models, a.out)
    sources.run_all(cd, a.out)
    info["seconds"] = round(time.time() - t0)
    json.dump(info, open(os.path.join(a.out, "run_info.json"), "w"), indent=1)
    print("DONE", json.dumps(info))


if __name__ == "__main__":
    main()
