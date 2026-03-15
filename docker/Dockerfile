FROM node:20-alpine

WORKDIR /app

# Install dependencies
RUN apk add --no-cache python3 py3-pip git

# Copy workspace
COPY . /app/workspace

# Install Python deps
RUN pip3 install --no-cache-dir \
    gymnasium \
    stable-baselines3 \
    numpy \
    psycopg2-binary

# Expose port
EXPOSE 3000

# Start command
CMD ["node", "index.js"]
