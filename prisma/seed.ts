import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
  console.log('Seeding database...');

  // Reset db first
  await prisma.loginAttempt.deleteMany({});
  await prisma.comment.deleteMany({});
  await prisma.appointment.deleteMany({});
  await prisma.supportTicket.deleteMany({});
  await prisma.transaction.deleteMany({});
  await prisma.record.deleteMany({});

  // 10 fake records
  const records = [
    {
      recordNo: "LND-2026-0001",
      ownerDisplayName: "Maria Santos",
      location: "123 Maple Street",
      city: "Pasig",
      classification: "Residential",
      status: "Verified",
      lastUpdated: "2026-05-01",
    },
    {
      recordNo: "LND-2026-0002",
      ownerDisplayName: "Daniel Reyes",
      location: "456 Oak Avenue",
      city: "Cainta",
      classification: "Commercial",
      status: "Pending Revision",
      lastUpdated: "2026-05-15",
    },
    {
      recordNo: "LND-2026-0003",
      ownerDisplayName: "Elena Cruz",
      location: "789 Pine Road",
      city: "Marikina",
      classification: "Residential",
      status: "Verified",
      lastUpdated: "2026-04-20",
    },
    {
      recordNo: "LND-2026-0004",
      ownerDisplayName: "Ramon Garcia",
      location: "101 Cedar Lane",
      city: "Quezon City",
      classification: "Agricultural",
      status: "Verified",
      lastUpdated: "2026-05-10",
    },
    {
      recordNo: "LND-2026-0005",
      ownerDisplayName: "Ana Villanueva",
      location: "202 Birch Court",
      city: "Pasig",
      classification: "Residential",
      status: "Disputed",
      lastUpdated: "2026-05-22",
    },
    {
      recordNo: "LND-2026-0006",
      ownerDisplayName: "Roberto Lim",
      location: "303 Walnut Way",
      city: "Cainta",
      classification: "Industrial",
      status: "Verified",
      lastUpdated: "2026-03-30",
    },
    {
      recordNo: "LND-2026-0007",
      ownerDisplayName: "Sample Holdings Corp.",
      location: "404 Chestnut Drive",
      city: "Marikina",
      classification: "Commercial",
      status: "Verified",
      lastUpdated: "2026-05-05",
    },
    {
      recordNo: "LND-2026-0008",
      ownerDisplayName: "Metro Registry Entity A",
      location: "505 Willow Boulevard",
      city: "Quezon City",
      classification: "Residential",
      status: "Pending Revision",
      lastUpdated: "2026-05-28",
    },
    {
      recordNo: "LND-2026-0009",
      ownerDisplayName: "Demo Resident A",
      location: "606 Cypress Lane",
      city: "Pasig",
      classification: "Commercial",
      status: "Verified",
      lastUpdated: "2026-04-12",
    },
    {
      recordNo: "LND-2026-0010",
      ownerDisplayName: "Demo Owner B",
      location: "707 Magnolia Court",
      city: "Quezon City",
      classification: "Residential",
      status: "Verified",
      lastUpdated: "2026-05-30",
    },
  ];

  for (const rec of records) {
    await prisma.record.create({ data: rec });
  }

  // 5 fake transactions
  const transactions = [
    {
      referenceNo: "TXN-100201",
      recordNo: "LND-2026-0001",
      serviceType: "Certified Copy Request",
      applicantName: "Maria Santos",
      email: "maria.santos@example.com",
      purpose: "Bank Loan Requirement",
      deliveryOption: "Printed certified copy",
      remarks: "Please prepare the copy for review.",
      status: "Dispatched",
    },
    {
      referenceNo: "TXN-100202",
      recordNo: "LND-2026-0003",
      serviceType: "Certified Copy Request",
      applicantName: "Daniel Reyes",
      email: "daniel.reyes@example.com",
      purpose: "Property Sale Transfer",
      deliveryOption: "Office Pickup",
      remarks: "Will pick up personally.",
      status: "Processing",
    },
    {
      referenceNo: "TXN-100203",
      recordNo: null,
      serviceType: "Land Classification History",
      applicantName: "Elena Cruz",
      email: "elena.cruz@example.com",
      purpose: "Research Study",
      deliveryOption: "Digital copy",
      remarks: "For civic history study.",
      status: "Completed",
    },
    {
      referenceNo: "TXN-100204",
      recordNo: "LND-2026-0004",
      serviceType: "Certified Copy Request",
      applicantName: "Ramon Garcia",
      email: "ramon.garcia@example.com",
      purpose: "Tax Declaration update",
      deliveryOption: "Office Pickup",
      remarks: "",
      status: "Pending Action",
    },
    {
      referenceNo: "TXN-100205",
      recordNo: "LND-2026-0007",
      serviceType: "Technical Description Verification",
      applicantName: "Ana Villanueva",
      email: "ana.villanueva@example.com",
      purpose: "Boundary Discrepancy Clarification",
      deliveryOption: "Digital copy",
      remarks: "Adjoining lot owner filed a minor boundary claim.",
      status: "Processing",
    },
  ];

  for (const txn of transactions) {
    await prisma.transaction.create({ data: txn });
  }

  // 3 fake comments
  const comments = [
    {
      displayName: "Maria Santos",
      message: "The record search page was easy to understand.",
    },
    {
      displayName: "Daniel Reyes",
      message: "I was able to find the sample transaction reference.",
    },
    {
      displayName: "Elena Cruz",
      message: "The appointment request form was clear.",
    },
  ];

  for (const comm of comments) {
    await prisma.comment.create({ data: comm });
  }

  console.log('Database seeded successfully.');
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
