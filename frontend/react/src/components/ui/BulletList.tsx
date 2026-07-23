interface BulletListProps {
  items: string[];
}

// A plain bulleted list with generous spacing between items - used
// anywhere a set of already-discrete strings (talking points, discovery
// questions, next steps, risks, ...) needs to read as separate items
// rather than a wall of text.
export function BulletList({ items }: BulletListProps) {
  return (
    <ul className="bullet-list">
      {items.map((item, index) => (
        <li key={index} className="bullet-list-item">
          {item}
        </li>
      ))}
    </ul>
  );
}
