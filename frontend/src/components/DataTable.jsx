import EmptyState from "./EmptyState";

export default function DataTable({ columns, rows, rowKey = "id", onRow, emptyTitle = "Nothing to show", emptyBody }) {
  if (!rows?.length) {
    return <EmptyState title={emptyTitle} body={emptyBody} />;
  }
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-left text-sm">
        <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
          <tr>
            {columns.map((column) => (
              <th key={column.key} className="whitespace-nowrap px-4 py-3 font-medium">
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={row[rowKey]}
              onClick={onRow ? () => onRow(row) : undefined}
              className={`border-t border-slate-100 ${onRow ? "cursor-pointer hover:bg-slate-50" : ""}`}
            >
              {columns.map((column) => (
                <td key={column.key} className="px-4 py-3 align-middle text-slate-700">
                  {column.render ? column.render(row) : row[column.key] ?? "—"}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
