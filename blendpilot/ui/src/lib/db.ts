import { PrismaClient } from "@prisma/client";
import { PrismaBetterSqlite3 } from "@prisma/adapter-better-sqlite3";
import path from "path";
import fs from "fs";

const globalForPrisma = globalThis as unknown as {
  prisma: PrismaClient | undefined;
};

function createPrismaClient() {
  const rootDb = path.resolve(process.cwd(), "dev.db");
  const prismaDirDb = path.resolve(process.cwd(), "prisma/dev.db");

  // Use the one with valid file size (>0)
  let targetDb = rootDb;
  if (fs.existsSync(rootDb) && fs.statSync(rootDb).size > 0) {
    targetDb = rootDb;
  } else if (fs.existsSync(prismaDirDb) && fs.statSync(prismaDirDb).size > 0) {
    targetDb = prismaDirDb;
  }

  const adapter = new PrismaBetterSqlite3({
    url: targetDb,
  });
  return new PrismaClient({
    adapter,
    log: process.env.NODE_ENV === "development" ? ["error", "warn"] : ["error"],
  });
}

export const db = globalForPrisma.prisma ?? createPrismaClient();

if (process.env.NODE_ENV !== "production") globalForPrisma.prisma = db;
