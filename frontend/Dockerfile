FROM node:20-slim
WORKDIR /app
COPY package.json ./
RUN npm install --no-audit --no-fund || true
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev"]
