const { PrismaClient } = require('@prisma/client');
const { Pool } = require('pg');
const { PrismaPg } = require('@prisma/adapter-pg');

const pool = new Pool({ connectionString: 'postgresql://blendpilot:blendpilot@localhost:5432/blendpilot?schema=public' });
const adapter = new PrismaPg(pool);
const prisma = new PrismaClient({ adapter });

prisma.project.findMany()
  .then(console.log)
  .catch(console.error)
  .finally(() => prisma.$disconnect());
