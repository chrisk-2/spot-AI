export default function StarfleetDashboard() {
  const data = {
    timestamp: "2026-05-15T17:47:39Z",
    result: "PASS",
    summary: {
      hosts_ping: "13/13",
      services: "24/24",
      warnings: 0,
    },
    hosts: [
      { host: "opnsense", ip: "192.168.1.1", role: "OPNsense", health: "OK", latency: 0.15, services: "443:OK" },
      { host: "dns-core", ip: "192.168.60.10", role: "DNS Core", health: "OK", latency: 0.65, services: "22:OK 53:OK" },
      { host: "starfleet-core", ip: "192.168.60.20", role: "NPM/UniFi", health: "OK", latency: 0.32, services: "22:OK 80:OK 443:OK 8443:OK" },
      { host: "spot-core", ip: "192.168.60.30", role: "Spot Core", health: "OK", latency: 0.04, services: "22:OK 8787:OK" },
      { host: "unimatrix6", ip: "192.168.50.10", role: "NAS/NFS", health: "OK", latency: 0.23, services: "2049:OK" },
      { host: "starfleet-tower", ip: "192.168.30.5", role: "Tower", health: "OK", latency: 0.31, services: "22:OK" },
      { host: "spot-worker-01", ip: "192.168.10.10", role: "General", health: "OK", latency: 0.62, services: "22:OK 11434:OK" },
      { host: "spot-worker-02", ip: "192.168.10.11", role: "Utility", health: "OK", latency: 0.21, services: "22:OK 11434:OK" },
      { host: "spot-ui-01", ip: "192.168.10.12", role: "UI", health: "OK", latency: 0.81, services: "22:OK" },
      { host: "spot-worker-03", ip: "192.168.10.13", role: "Coding", health: "OK", latency: 0.63, services: "22:OK 11434:OK" },
      { host: "spot-worker-04", ip: "192.168.10.14", role: "Heavy", health: "OK", latency: 0.42, services: "22:OK 11434:OK" },
      { host: "spot-worker-05", ip: "192.168.10.15", role: "Review", health: "OK", latency: 0.35, services: "22:OK 11434:OK" },
      { host: "spot-worker-06", ip: "192.168.10.16", role: "Reasoning", health: "OK", latency: 0.31, services: "22:OK 11434:OK" },
    ],
  };

  const healthColor = {
    OK: "bg-green-500",
    WARN: "bg-yellow-500",
    FAIL: "bg-red-500",
  };

  return (
    <div className="min-h-screen bg-black text-white p-6 font-mono">
      <div className="max-w-7xl mx-auto space-y-6">
        <div className="rounded-3xl border border-zinc-800 bg-zinc-950 p-6 shadow-2xl">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <h1 className="text-4xl font-bold tracking-tight">
                STARFLEET STATUS
              </h1>
              <p className="text-zinc-400 mt-2">
                One-screen fleet health overview
              </p>
            </div>

            <div className="flex items-center gap-3">
              <div className="h-5 w-5 rounded-full bg-green-500 animate-pulse" />
              <div>
                <div className="text-2xl font-bold text-green-400">
                  ALL SYSTEMS ONLINE
                </div>
                <div className="text-sm text-zinc-500">
                  Last update: {data.timestamp}
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="rounded-2xl bg-zinc-950 border border-zinc-800 p-5">
            <div className="text-zinc-500 text-sm">Hosts Online</div>
            <div className="text-4xl font-bold mt-2 text-green-400">
              {data.summary.hosts_ping}
            </div>
          </div>

          <div className="rounded-2xl bg-zinc-950 border border-zinc-800 p-5">
            <div className="text-zinc-500 text-sm">Services Healthy</div>
            <div className="text-4xl font-bold mt-2 text-cyan-400">
              {data.summary.services}
            </div>
          </div>

          <div className="rounded-2xl bg-zinc-950 border border-zinc-800 p-5">
            <div className="text-zinc-500 text-sm">Warnings</div>
            <div className="text-4xl font-bold mt-2 text-yellow-400">
              {data.summary.warnings}
            </div>
          </div>

          <div className="rounded-2xl bg-zinc-950 border border-zinc-800 p-5">
            <div className="text-zinc-500 text-sm">Control Plane</div>
            <div className="text-2xl font-bold mt-3 text-green-400">
              SPOT CORE OK
            </div>
          </div>
        </div>

        <div className="rounded-3xl bg-zinc-950 border border-zinc-800 overflow-hidden">
          <div className="px-6 py-4 border-b border-zinc-800 flex items-center justify-between">
            <h2 className="text-2xl font-bold">Fleet Nodes</h2>
            <div className="text-zinc-500 text-sm">
              Green = good. Red = broken. No archaeology required.
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead className="bg-zinc-900 text-zinc-400 text-sm uppercase tracking-wide">
                <tr>
                  <th className="px-6 py-4">Health</th>
                  <th className="px-6 py-4">Host</th>
                  <th className="px-6 py-4">Role</th>
                  <th className="px-6 py-4">IP</th>
                  <th className="px-6 py-4">Latency</th>
                  <th className="px-6 py-4">Services</th>
                </tr>
              </thead>

              <tbody>
                {data.hosts.map((host) => (
                  <tr
                    key={host.host}
                    className="border-t border-zinc-800 hover:bg-zinc-900/60"
                  >
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div
                          className={`h-4 w-4 rounded-full ${healthColor[host.health]}`}
                        />
                        <span className="font-bold">{host.health}</span>
                      </div>
                    </td>

                    <td className="px-6 py-4 font-bold text-lg">
                      {host.host}
                    </td>

                    <td className="px-6 py-4 text-zinc-300">
                      {host.role}
                    </td>

                    <td className="px-6 py-4 text-cyan-300">
                      {host.ip}
                    </td>

                    <td className="px-6 py-4">
                      {host.latency} ms
                    </td>

                    <td className="px-6 py-4 text-sm text-zinc-400">
                      {host.services}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="rounded-2xl bg-zinc-950 border border-zinc-800 p-5">
            <div className="text-zinc-500 text-sm mb-2">General Lane</div>
            <div className="text-xl font-bold text-green-400">
              worker-01 ONLINE
            </div>
          </div>

          <div className="rounded-2xl bg-zinc-950 border border-zinc-800 p-5">
            <div className="text-zinc-500 text-sm mb-2">Coding Lane</div>
            <div className="text-xl font-bold text-green-400">
              worker-03 ONLINE
            </div>
          </div>

          <div className="rounded-2xl bg-zinc-950 border border-zinc-800 p-5">
            <div className="text-zinc-500 text-sm mb-2">Heavy/Reasoning</div>
            <div className="text-xl font-bold text-green-400">
              worker-04 + worker-06 ONLINE
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
