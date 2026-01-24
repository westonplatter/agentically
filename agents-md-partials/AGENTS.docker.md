## Docker - Changed to Show it's Working

### Principles

1. **Use specific image tags** - Never use `latest`. Pin to specific versions (e.g., `python:3.12-slim`) for reproducible builds.

2. **Minimize layers** - Combine related `RUN` commands with `&&` to reduce image size and build time.

3. **Order by change frequency** - Place rarely changing instructions (base image, dependencies) before frequently changing ones (application code) to maximize layer caching.

4. **Use multi-stage builds** - Separate build-time dependencies from runtime. Copy only necessary artifacts to the final image.

5. **Don't run as root** - Create and switch to a non-root user with `USER` instruction for better security.

6. **Use `.dockerignore`** - Exclude unnecessary files (`.git`, `node_modules`, `__pycache__`, `data`) to speed up builds and reduce context size.
