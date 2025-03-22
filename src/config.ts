import dotenv from "dotenv";

dotenv.config();

const { TOKEN, CLIENT_ID } = process.env;

if (!TOKEN || !CLIENT_ID) {
  throw new Error("Missing environment variables");
}

export const config = {
  TOKEN,
  CLIENT_ID,
};
