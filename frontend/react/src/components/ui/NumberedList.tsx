interface NumberedListProps {
  items: string[];
}

// Each item gets its own row with a large number badge, so a reader can
// tell at a glance how many recommendations/talking points there are
// without parsing a run-on paragraph.
export function NumberedList({ items }: NumberedListProps) {
  return (
    <ol className="numbered-list">
      {items.map((item, index) => (
        <li key={index} className="numbered-list-item">
          <span className="numbered-list-index">{index + 1}</span>
          <span className="numbered-list-text">{item}</span>
        </li>
      ))}
    </ol>
  );
}
