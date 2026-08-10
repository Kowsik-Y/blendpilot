import { auth } from "@/lib/auth";
import { db } from "@/lib/db";
import { redirect } from "next/navigation";

export default async function ChatIndexPage() {
  const session = await auth();
  if (!session?.user?.id) {
    redirect("/login");
  }

  // Find most recent session or create a new one
  let chatSession = await db.chatSession.findFirst({
    where: { userId: session.user.id },
    orderBy: { updatedAt: "desc" },
  });


  redirect(`/projects}`);
}
