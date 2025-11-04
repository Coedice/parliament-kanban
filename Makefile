.PHONY: generate
generate:
	uv run python main.py

.PHONY: build
build:
	@docker run --rm -v "$$PWD:/srv/jekyll" -p 8080:8080 -it jekyll/jekyll:latest /bin/sh -c " \
		rm -f Gemfile.lock; \
		bundle install; \
		bundle exec jekyll serve -H 0.0.0.0 -P 8080 \
	"

.PHONY: format
format:
	isort .
	ruff format

.PHONY: clean
clean:
	rm -rf _site/
	rm -rf .venv/
	rm -rf .ruff_cache/
	rm -rf __pycache__/
	rm -rf .sass-cache/
	rm -rf .jekyll-cache/
	rm -rf .jekyll-metadata
	rm -rf .bundle/
	rm -rf vendor/
	rm -f Gemfile.lock
	rm -f *.pyc
	rm -f _data/bills.yml.tmp
	rm -f uv.lock
