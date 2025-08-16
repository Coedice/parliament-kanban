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