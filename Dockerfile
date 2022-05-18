# ============================= BASE =============================
# Get official base image
FROM python:3.8.2-slim-buster AS base
# Set the working directory. Note, this must be done prior to adding the user as chown will fail on no such directory.
WORKDIR /app
# Add a user
RUN useradd -m app
RUN chown -R app:app /app
ENV PATH="/home/app/.local/bin:${PATH}"
USER app
# Get the dependencies
COPY requirements.txt requirements.txt
RUN pip install --user --upgrade pip
RUN pip install --user -r requirements.txt
RUN pip install --user gunicorn
# Setup the environment
COPY static static
COPY templates templates
COPY app.py boot.sh ./
ENV FLASK_APP app.py

# # ========================= DEVELOPMENT ==========================
# FROM base AS development
# EXPOSE 5007
# CMD [ "flask", "run" ]

# ========================= PRODUCTION ===========================
FROM base AS production
EXPOSE 80
ENTRYPOINT ["/bin/bash", "./boot.sh"]

# # =========================== MANAGE =============================
# FROM base AS manage
# ENTRYPOINT [ "flask" ]
