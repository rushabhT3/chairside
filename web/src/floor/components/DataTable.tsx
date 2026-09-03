import { useRef, type KeyboardEvent, type ReactNode } from "react";

export interface Column<T> {
  key: string;
  header: string;
  numeric?: boolean;
  render: (row: T) => ReactNode;
}

export interface DataTableProps<T> {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  rowClass?: (row: T) => string | undefined;
  onSelect?: (row: T) => void;
  caption: string;
}

export function DataTable<T>({ columns, rows, rowKey, rowClass, onSelect, caption }: DataTableProps<T>) {
  const bodyRef = useRef<HTMLTableSectionElement>(null);

  const moveFocus = (from: HTMLTableRowElement, delta: number) => {
    const all = Array.from(bodyRef.current?.querySelectorAll<HTMLTableRowElement>("tr[tabindex]") ?? []);
    const next = all[all.indexOf(from) + delta];
    next?.focus();
  };

  const onRowKeyDown = (event: KeyboardEvent<HTMLTableRowElement>, row: T) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      moveFocus(event.currentTarget, 1);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      moveFocus(event.currentTarget, -1);
    } else if ((event.key === "Enter" || event.key === " ") && onSelect) {
      event.preventDefault();
      onSelect(row);
    }
  };

  return (
    <div className="table-wrap">
      <table className="table">
        <caption className="visually-hidden">{caption}</caption>
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.key} scope="col" className={c.numeric ? "num" : undefined}>
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody ref={bodyRef}>
          {rows.map((row, i) => (
            <tr
              key={rowKey(row)}
              className={rowClass?.(row)}
              tabIndex={onSelect ? (i === 0 ? 0 : -1) : undefined}
              onKeyDown={onSelect ? (e) => onRowKeyDown(e, row) : undefined}
              onClick={onSelect ? () => onSelect(row) : undefined}
            >
              {columns.map((c) => (
                <td key={c.key} className={c.numeric ? "num" : undefined}>
                  {c.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
