import Link from "next/link";
import { notFound } from "next/navigation";
import { prisma } from "@/lib/prisma";

export const dynamic = "force-dynamic";

export default async function RequestCopyPage({
  params,
}: {
  params: Promise<{ recordNo: string }>;
}) {
  const { recordNo } = await params;
  const record = await prisma.record.findUnique({
    where: { recordNo: recordNo.toUpperCase() },
  });

  if (!record) {
    notFound();
  }

  return (
    <main className="bg-slate-50 px-4 py-10">
      <div className="mx-auto w-full max-w-2xl rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-100 px-6 py-6">
          <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-slate-500">
            Land Records Demo Portal
          </p>
          <h1 className="mt-2 text-2xl font-extrabold tracking-tight text-slate-950">
            Request Certified Copy
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Submit a native form for record <span className="font-mono font-semibold text-slate-900">{record.recordNo}</span>.
          </p>
        </div>

        <form
          action={`/records/${record.recordNo}/request-copy/submit`}
          method="post"
          className="space-y-5 px-4 py-6 sm:px-6"
          noValidate
        >
          <div className="space-y-1.5">
            <label htmlFor="copy-fullName" className="block text-xs font-bold uppercase tracking-wider text-slate-600">
              Full Name <span aria-hidden="true" className="text-rose-600">*</span>
            </label>
            <input
              id="copy-fullName"
              name="fullName"
              type="text"
              required
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none ring-offset-2 focus:ring-2 focus:ring-blue-600 min-h-11"
            />
          </div>

          <div className="space-y-1.5">
            <label htmlFor="copy-email" className="block text-xs font-bold uppercase tracking-wider text-slate-600">
              Email <span aria-hidden="true" className="text-rose-600">*</span>
            </label>
            <input
              id="copy-email"
              name="email"
              type="email"
              required
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none ring-offset-2 focus:ring-2 focus:ring-blue-600 min-h-11"
            />
          </div>

          <div className="space-y-1.5">
            <label htmlFor="copy-purpose" className="block text-xs font-bold uppercase tracking-wider text-slate-600">
              Purpose <span aria-hidden="true" className="text-rose-600">*</span>
            </label>
            <select
              id="copy-purpose"
              name="purpose"
              required
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none ring-offset-2 focus:ring-2 focus:ring-blue-600 min-h-11"
            >
              <option value="">Select a purpose</option>
              <option value="Personal Ownership Verification">Personal Ownership Verification</option>
              <option value="Mortgage / Collateral Review">Mortgage / Collateral Review</option>
              <option value="Legal Boundary Dispute Resolution">Legal Boundary Dispute Resolution</option>
              <option value="Subdivision Mapping Submission">Subdivision Mapping Submission</option>
            </select>
          </div>

          <div className="space-y-3">
            <p className="text-xs font-bold uppercase tracking-wider text-slate-600">
              Delivery Option <span aria-hidden="true" className="text-rose-600">*</span>
            </p>
            <label className="flex min-h-11 items-center gap-3 rounded-lg border border-slate-200 px-4 py-3">
              <input type="radio" name="deliveryOption" value="Digital copy" defaultChecked required />
              <span className="text-sm text-slate-900">Digital copy</span>
            </label>
            <label className="flex min-h-11 items-center gap-3 rounded-lg border border-slate-200 px-4 py-3">
              <input type="radio" name="deliveryOption" value="Printed certified copy" required />
              <span className="text-sm text-slate-900">Printed certified copy</span>
            </label>
          </div>

          <div className="space-y-1.5">
            <label htmlFor="copy-remarks" className="block text-xs font-bold uppercase tracking-wider text-slate-600">
              Remarks
            </label>
            <textarea
              id="copy-remarks"
              name="remarks"
              rows={3}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none ring-offset-2 focus:ring-2 focus:ring-blue-600"
            />
          </div>

          <button
            type="submit"
            className="w-full rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-bold text-white transition-colors hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-2 min-h-11"
          >
            Submit request
          </button>
        </form>

        <div className="border-t border-slate-100 px-6 py-4 text-xs text-slate-500">
          <Link href={`/records/${record.recordNo}`} className="font-semibold text-blue-700 hover:underline">
            Back to record
          </Link>
        </div>
      </div>
    </main>
  );
}
