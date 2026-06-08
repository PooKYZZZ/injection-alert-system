import React from 'react';
import Container from './Container';

export default function SiteFooter() {
  return (
    <footer className="bg-white text-slate-650 text-xs py-10 border-t border-gray-200">
      <Container>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-8 text-sm">
          <div>
            <h3 className="text-[#002147] font-bold uppercase tracking-wider text-xs mb-3">Portal Services</h3>
            <ul className="space-y-2 text-slate-500 font-medium">
              <li>Open Data Land Registries</li>
              <li>Official Titling Verification</li>
              <li>Boundary Disputes & Survey Registers</li>
              <li>Certified Copy Dispatches</li>
            </ul>
          </div>
          <div>
            <h3 className="text-[#002147] font-bold uppercase tracking-wider text-xs mb-3">Support & Branch Locations</h3>
            <ul className="space-y-2 text-slate-500 font-medium">
              <li>Pasig Central Office - City Hall Complex</li>
              <li>Cainta Branch Office - Municipal Administrative Center</li>
              <li>Marikina Branch - Riverbanks District</li>
              <li>Quezon City Head Office - East Ave</li>
            </ul>
          </div>
          <div>
            <h3 className="text-[#002147] font-bold uppercase tracking-wider text-xs mb-3">Technical Notes</h3>
            <p className="leading-relaxed text-slate-450 text-slate-500 text-xs italic">
              This system is a synthetic, high-fidelity mock website for local registry simulation. Do not enter real sensitive credentials.
            </p>
          </div>
        </div>
        <div className="border-t border-gray-150 pt-6 flex flex-col sm:flex-row justify-between items-center gap-4 text-slate-400 font-medium text-[11px]">
          <p>© 2026 Land Records Demo Portal. Built for local demonstration only.</p>
          <div className="flex gap-4 uppercase tracking-wider font-bold text-slate-500">
            <span className="hover:text-blue-700 cursor-pointer">Privacy Policy</span>
            <span>•</span>
            <span className="hover:text-blue-700 cursor-pointer">Terms of Service</span>
          </div>
        </div>
      </Container>
    </footer>
  );
}
