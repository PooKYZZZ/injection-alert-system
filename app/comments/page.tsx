import React from 'react';
import Link from 'next/link';
import type { Comment } from '@prisma/client';
import { prisma } from '@/lib/prisma';
import { MessageSquare, Send, User, MessageCircleCode, CheckCircle2, AlertCircle } from 'lucide-react';
import Container from '@/components/Container';
import Card from '@/components/Card';
import NoticeBanner from '@/components/NoticeBanner';

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
        <h2 className="text-2xl md:text-3xl font-extrabold text-slate-950 flex items-center gap-2">
          <MessageSquare className="w-7 h-7 text-blue-600" />
          <span>Public Citizen Comments</span>
        </h2>
        <p className="text-slate-500 text-sm mt-1">
          Read sample public feedback about search, status tracking, and appointment requests.
        </p>
      </div>

      {success && (
        <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg p-5 space-y-1">
          <h3 className="font-bold text-base flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5 text-emerald-600" />
            <span>Comment Published Successfully!</span>
          </h3>
          <p className="text-xs">
            Your comment is now visible on this demo feedback page.
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
            <span>Citizen Comments ({commentsList.length})</span>
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
                No comments exist yet. Be the first to lodge a message!
              </Card>
            )}
          </div>
        </div>

        {/* Right Column: Add Comment Form */}
        <div>
          <Card className="p-6 space-y-4">
            <h3 className="text-sm font-bold text-slate-900 border-b border-gray-100 pb-2 flex items-center gap-1.5 uppercase tracking-wider">
              <MessageCircleCode className="w-5 h-5 text-blue-600" />
              <span>Leave a Comment</span>
            </h3>

            <form method="POST" action="/comments/submit" className="space-y-4">
              <div className="space-y-1">
                <label htmlFor="displayName" className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                  Your Identifier Name <span className="text-rose-500">*</span>
                </label>
                <div className="relative">
                  <User className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                  <input
                    id="displayName"
                    type="text"
                    name="displayName"
                    required
                    placeholder="Enter name or alias..."
                    className="w-full min-h-11 pl-9 pr-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm focus:ring-1 focus:ring-blue-500 focus:border-blue-500 bg-white"
                  />
                </div>
              </div>

              <div className="space-y-1">
                <label htmlFor="message" className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                  Comment Message <span className="text-rose-500">*</span>
                </label>
                <textarea
                  id="message"
                  name="message"
                  required
                  rows={4}
                    placeholder="Share your experience with this demo portal..."
                  className="w-full p-3 border border-gray-300 rounded-md shadow-sm text-sm focus:ring-1 focus:ring-blue-500 focus:border-blue-500 bg-white"
                ></textarea>
              </div>

              <button
                type="submit"
                className="w-full min-h-11 bg-blue-600 hover:bg-blue-700 text-white font-bold text-sm py-2.5 px-4 rounded shadow-sm transition-colors flex items-center justify-center gap-1.5"
              >
                <Send className="w-3.5 h-3.5" />
                <span>Publish Comment</span>
              </button>
            </form>
          </Card>
        </div>
      </div>
    </Container>
  );
}
