FROM node:20-alpine

WORKDIR /app

COPY apps/web/package.json apps/web/package-lock.json* ./
RUN npm ci

COPY apps/web .

EXPOSE 3001

CMD ["npm", "run", "dev"]
