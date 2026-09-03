export interface PhotoPickerProps {
  onPick: (file: File | undefined) => void;
}

export function PhotoPicker({ onPick }: PhotoPickerProps) {
  return (
    <label className="file-pick">
      <span className="btn btn-secondary">Choose a photo</span>
      <input
        className="file-input"
        type="file"
        accept="image/*"
        capture="user"
        onChange={(event) => onPick(event.target.files?.[0])}
      />
    </label>
  );
}
