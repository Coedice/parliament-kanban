build:
	@docker run --rm -v "$$PWD:/var/jekyll" -p 8080:8080 -it mrxder/jekyll-docker-arm64:latest /bin/sh -c "\
		bundle install; \
		bundle exec jekyll serve -H 0.0.0.0 -P 8080 \
	"
