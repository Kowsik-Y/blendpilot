// Prisma 7 configuration file
export default {
  schema: "prisma/schema.prisma",
  datasource: {
    url: process.env.DATABASE_URL || "postgresql://blendpilot:blendpilot@localhost:5432/blendpilot?schema=public",
  },
};
