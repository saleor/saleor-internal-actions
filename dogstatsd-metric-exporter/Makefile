CODE_PATH=dogstatsd_metric_exporter/ tests/ example/ ./setup.py

clean:
	python -m black $(CODE_PATH)
	python -m isort $(CODE_PATH)

install-devel:
	pip install '.[dev]'
