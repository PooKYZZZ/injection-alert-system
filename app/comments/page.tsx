import React from 'react';
import Link from 'next/link';
import type { Comment } from '@prisma/client';
import { prisma } from '@/lib/prisma';
import { MessageSquare, User, CheckCircle2, AlertCircle } from 'lucide-react';
import Container from '@/components/Container';
import Card from '@/components/Card';
import NoticeBanner from '@/components/NoticeBanner';
import CommentsForm from '../CommentsForm';

interface CommentsPageProps {
  searchParams: Promise<{ success?: string; posted?: string }>;
}

export default async function CommentsPage({ searchParams }: CommentsPageProps) {
  const awaitedParams = await searchParams;
  const success = awaitedParams.success === 'true' || awaitedParams.posted === '1';

  // Read comments dynamically from the database.
  const commentsList: Comment[] = await prisma.comment.findMany({
    orderBy: { createdAt: 'desc' },
  });

  return (
    <Container className="space-y-6">
      {/* Breadcrumbs */}
      <div className="flex items-center gap-1.5 text-xs text-slate-500 font-medium">
        <Link href="/" className="hover:underline hover:text-slate-700">Home</Link>
        <span>/</span>
        <span className="text-slate-800">Comments</span>
      </div>

      <div className="border-b border-gray-200 pb-4">
        <h1 className="text-2xl md:text-3xl font-extrabold text-slate-950 flex items-center gap-2">
          <MessageSquare aria-hidden="true" className="w-7 h-7 text-blue-600" />
          <span>Demo Comments</span>
        </h1>
        <p className="text-slate-500 text-sm mt-1">
          Read feedback about testing these mock workflows.
        </p>
      </div>

      {success && (
        <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg p-5 space-y-1">
          <h3 className="font-bold text-base flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5 text-emerald-600" />
            <span>Comment added to the demo page</span>
          </h3>
          <p className="text-xs">
            Your comment was added to this mock feedback page.
          </p>
        </div>
      )}

      <NoticeBanner
        message="Important: Please do not publish personal information, real landowner details, or sensitive reference numbers."
        type="warning"
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Comments List */}
        <div className="lg:col-span-2 space-y-4">
          <h3 className="text-sm font-bold text-slate-550 flex items-center gap-1.5 uppercase tracking-wider">
            <span>Comments ({commentsList.length})</span>
          </h3>

          <div className="space-y-4">
            {commentsList.map((comm) => (
              <Card key={comm.id} className="p-5 space-y-3 hover:border-slate-350 transition-colors">
                <div className="flex flex-col gap-2 border-b border-gray-100 pb-2 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex items-center gap-2">
                    <div className="bg-slate-100 p-1.5 rounded-full text-slate-650">
                      <User className="w-4 h-4 shadow-sm" />
                    </div>
                    <strong className="text-sm font-bold text-slate-900">{comm.displayName}</strong>
                  </div>
                  <span className="text-[10px] font-semibold text-slate-400 font-mono">
                    {new Date(comm.createdAt).toLocaleString()}
                  </span>
                </div>
                <p className="text-sm text-slate-700 leading-relaxed font-sans">{comm.message}</p>
              </Card>
            ))}

            {commentsList.length === 0 && (
              <Card className="p-12 text-center text-slate-400 font-medium">
              No comments yet. Add the first demo comment.
              </Card>
            )}
          </div>
        </div>

        {/* Right Column: Add Comment Form */}
        <div>
          <Card className="p-6">
            <CommentsForm />
          </Card>
        </div>
      </div>
    </Container>
  );
}
