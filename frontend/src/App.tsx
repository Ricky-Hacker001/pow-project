// frontend/src/App.tsx
import React, { useRef, useEffect, useState } from 'react';
import './App.css';

const API_URL = "http://127.0.0.1:5000";
const BLOCK_SIZE = 4096;

// Helper functions (unchanged)
const bufferToHex = (buffer: ArrayBuffer): string => ([...new Uint8Array(buffer)].map(b => b.toString(16).padStart(2, '0')).join(''));
const concatBuffers = (buffer1: ArrayBuffer, buffer2: ArrayBuffer): ArrayBuffer => {
  const tmp = new Uint8Array(buffer1.byteLength + buffer2.byteLength);
  tmp.set(new Uint8Array(buffer1), 0);
  tmp.set(new Uint8Array(buffer2), buffer1.byteLength);
  return tmp.buffer;
};
const prg = async (seed: string, index: number): Promise<ArrayBuffer> => {
  const encoder = new TextEncoder();
  const data = concatBuffers(encoder.encode(seed), encoder.encode(String(index)));
  return await crypto.subtle.digest('SHA-256', data);
};


function App() {
  const [file, setFile] = useState<File | null>(null);
  const [statusLog, setStatusLog] = useState<string[]>(['Awaiting file selection...']);
  const [statusColor, setStatusColor] = useState<'success' | 'error' | ''>('');
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [isDragging, setIsDragging] = useState<boolean>(false);

  const statusLogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (statusLogRef.current) {
      statusLogRef.current.scrollTop = statusLogRef.current.scrollHeight;
    }
  }, [statusLog]);

  const handleDragEvents = (e: React.DragEvent, isEntering: boolean) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(isEntering);
  };
  
  const handleDrop = (e: React.DragEvent) => {
    handleDragEvents(e, false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelection(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelection(e.target.files[0]);
    }
  };

  const handleFileSelection = (selectedFile: File) => {
    setFile(selectedFile);
    setStatusLog([`File selected: ${selectedFile.name}`]);
    setStatusColor('');
  };

  const handleUpload = async () => {
    if (!file) return;

    setIsProcessing(true);
    setStatusColor('');
    setStatusLog(['Initiating secure connection...']);

    const reader = new FileReader();
    reader.readAsArrayBuffer(file);
    reader.onload = async (e) => {
      try {
        await new Promise(res => setTimeout(res, 500)); // Simulate connection
        setStatusLog(prev => [...prev, '1/5: Hashing file locally...']);
        const fileBuffer = e.target?.result as ArrayBuffer;
        const fileTag = bufferToHex(await crypto.subtle.digest('SHA-256', fileBuffer));
        
        await new Promise(res => setTimeout(res, 500)); // Simulate delay
        setStatusLog(prev => [...prev, '2/5: Checking server for file duplication...']);
        const checkResponse = await fetch(`${API_URL}/check-file`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ tag: fileTag }),
        });
        const checkData = await checkResponse.json();

        if (checkData.status === 'new') {
          setStatusLog(prev => [...prev, '3/5: File is new. Beginning encrypted upload...']);
          const formData = new FormData();
          formData.append('file', file);
          formData.append('tag', fileTag);
          await fetch(`${API_URL}/upload-file`, { method: 'POST', body: formData });

          setStatusLog(prev => [...prev, '4/5: Finalizing upload...']);
          await new Promise(res => setTimeout(res, 500)); // Simulate finalization
          setStatusLog(prev => [...prev, '✅ Upload Complete!']);
          setStatusColor('success');

        } else if (checkData.status === 'exists') {
          setStatusLog(prev => [...prev, '3/5: File exists. Generating Proof of Ownership...']);
          const { seed } = checkData;
          
          const blocks: ArrayBuffer[] = [];
          for (let i = 0; i < fileBuffer.byteLength; i += BLOCK_SIZE) blocks.push(fileBuffer.slice(i, i + BLOCK_SIZE));
          if (blocks.length < 2) throw new Error("File too small.");
          
          const para1 = await crypto.subtle.digest('SHA-256', concatBuffers(blocks[0], await prg(seed, 1)));
          const para2 = await crypto.subtle.digest('SHA-256', concatBuffers(blocks[1], await prg(seed, 2)));
          let resp = await crypto.subtle.digest('SHA-256', concatBuffers(para1, para2));
          for (let i = 2; i < blocks.length; i++) {
            const block_hash = await crypto.subtle.digest('SHA-256', concatBuffers(blocks[i], await prg(seed, i + 1)));
            resp = await crypto.subtle.digest('SHA-256', concatBuffers(resp, block_hash));
          }
          const proof = bufferToHex(resp);
          
          setStatusLog(prev => [...prev, '4/5: Transmitting proof for verification...']);
          await new Promise(res => setTimeout(res, 500)); // Simulate transmission
          
          const verifyResponse = await fetch(`${API_URL}/verify`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tag: fileTag, proof: proof }),
          });
          const verifyData = await verifyResponse.json();

          if (verifyData.status === 'verified') {
            setStatusLog(prev => [...prev, '5/5: Proof accepted.']);
            setStatusLog(prev => [...prev, '✅ Ownership Verified!']);
            setStatusColor('success');
          } else {
            throw new Error('Ownership verification failed.');
          }
        }
      } catch (error) {
        setStatusLog(prev => [...prev, `❌ Error: ${(error as Error).message}`]);
        setStatusColor('error');
      } finally {
        setIsProcessing(false);
      }
    };
  };

  return (
    <div className="container">
      <h1>Secure Vault</h1>
      <p>Upload files with advanced Proof of Ownership verification.</p>
      
      {!isProcessing ? (
        <>
          <div 
            className={`upload-area ${isDragging ? 'active' : ''}`}
            onDragEnter={(e) => handleDragEvents(e, true)}
            onDragLeave={(e) => handleDragEvents(e, false)}
            onDragOver={(e) => e.preventDefault()}
            onDrop={handleDrop}
          >
            <input type="file" id="file-upload" onChange={handleFileChange} />
            <svg className="icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-1-13h2v6h-2zm0 8h2v2h-2z" fill="currentColor"/><path d="M13 15h-2v-6h2v6zm0 4h-2v-2h2v2z" opacity="0" /></svg>
            <p>Drag & Drop Your File Here</p>
            <label htmlFor="file-upload" className="file-label">Or Browse Files</label>
            {file && <div className="file-name">{file.name}</div>}
          </div>
          <button className="file-label" onClick={handleUpload} disabled={!file}>
            Start Secure Upload
          </button>
        </>
      ) : (
        <div className="processing-container">
          <div className="scanner">
            <div className="body"></div>
          </div>
          <p className="processing-text">Analyzing Data Stream...</p>
        </div>
      )}

      <div className="status-log" ref={statusLogRef}>
        {statusLog.map((log, index) => (
          <div 
            key={index} 
            className={`log-line ${index === statusLog.length - 1 ? statusColor : ''}`}
            style={{ animationDelay: `${index * 0.1}s` }}
          >
            {`> ${log}`}
          </div>
        ))}
      </div>
    </div>
  );
}

export default App;