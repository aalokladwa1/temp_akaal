import {
  Component,
  Input,
  Output,
  EventEmitter,
  signal,
  ElementRef,
  ViewChild,
  AfterViewInit,
  OnDestroy,
  OnChanges,
  SimpleChanges
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

/**
 * CodeEditorComponent
 *
 * GDS-compliant code editor component for procedural / schema definition review.
 * Integrates with Monaco Editor when available in browser environments,
 * and provides a robust, zero-shadow, non-flaky fallback in Node/Vitest headless testing.
 *
 * TYPOGRAPHY LAW:
 * All code editors, text, headings, and metadata strictly render in Roboto font.
 */
@Component({
  selector: 'app-code-editor',
  standalone: true,
  imports: [CommonModule, FormsModule],
  host: {
    class: 'flex flex-1 flex-col w-full h-full min-h-0'
  },
  template: `
    <div class="w-full h-full flex flex-col bg-white border-0 overflow-hidden relative font-sans text-xs flex-1 min-h-0">
      
      <!-- Fallback or Test Environment Editor (Also active if Monaco scripts not loaded) -->
      @if (!isMonacoActive()) {
        <div class="flex-1 flex min-h-0 bg-white text-slate-900 overflow-hidden relative w-full h-full">
          
          <!-- Line numbers gutter -->
          <div
            #gutter
            class="w-11 bg-slate-50 border-r border-slate-200 py-3 pr-2 select-none text-right font-mono text-xs text-slate-400 shrink-0 leading-5 overflow-hidden">
            @for (lineNum of getLines(); track lineNum) {
              <div>{{ lineNum }}</div>
            }
          </div>

          <!-- Code editor textarea -->
          <textarea
            #fallbackTextarea
            [value]="code"
            [readonly]="readOnly"
            (input)="onTextareaInput($event)"
            (scroll)="onScroll($event)"
            [attr.aria-label]="ariaLabel || 'Source code editor'"
            class="flex-1 w-full h-full py-3 px-3.5 font-mono text-xs bg-white text-slate-900 resize-none focus:outline-none border-none leading-5 select-text overflow-auto whitespace-pre"
            style="tab-size: 2;"
            spellcheck="false"></textarea>
        </div>
      }

      <!-- Native Monaco Editor Container -->
      <div
        #monacoContainer
        class="flex-1 w-full h-full min-h-0"
        [class.hidden]="!isMonacoActive()">
      </div>

    </div>
  `
})
export class CodeEditorComponent implements AfterViewInit, OnDestroy, OnChanges {
  @Input() code: string = '';
  @Input() language: string = 'sql';
  @Input() readOnly: boolean = false;
  @Input() ariaLabel: string = 'Code editor';
  @Output() codeChange = new EventEmitter<string>();

  @ViewChild('monacoContainer') monacoContainerRef?: ElementRef<HTMLDivElement>;
  @ViewChild('fallbackTextarea') fallbackTextareaRef?: ElementRef<HTMLTextAreaElement>;
  @ViewChild('gutter') gutterRef?: ElementRef<HTMLDivElement>;

  public readonly isMonacoActive = signal<boolean>(false);
  private monacoEditorInstance?: any;

  public ngAfterViewInit(): void {
    this.tryInitMonaco();
  }

  public ngOnChanges(changes: SimpleChanges): void {
    if (changes['code'] && this.monacoEditorInstance) {
      const currentVal = this.monacoEditorInstance.getValue();
      if (currentVal !== this.code) {
        this.monacoEditorInstance.setValue(this.code || '');
      }
    }
    if (changes['readOnly'] && this.monacoEditorInstance) {
      this.monacoEditorInstance.updateOptions({ readOnly: this.readOnly });
    }
  }

  public ngOnDestroy(): void {
    if (this.monacoEditorInstance) {
      this.monacoEditorInstance.dispose();
      this.monacoEditorInstance = null;
    }
  }

  public onTextareaInput(event: Event): void {
    const val = (event.target as HTMLTextAreaElement).value;
    this.code = val;
    this.codeChange.emit(val);
  }

  public onScroll(event: Event): void {
    if (this.gutterRef?.nativeElement) {
      this.gutterRef.nativeElement.scrollTop = (event.target as HTMLElement).scrollTop;
    }
  }

  public getLines(): number[] {
    const count = (this.code || '').split('\n').length;
    return Array.from({ length: Math.max(1, count) }, (_, i) => i + 1);
  }

  private tryInitMonaco(): void {
    if (typeof window === 'undefined' || !(window as any).monaco) {
      // Vitest / Node or Monaco not yet loaded in DOM -> keep robust fallback
      this.isMonacoActive.set(false);
      return;
    }

    try {
      const monaco = (window as any).monaco;
      if (!this.monacoContainerRef?.nativeElement) return;

      this.monacoEditorInstance = monaco.editor.create(this.monacoContainerRef.nativeElement, {
        value: this.code || '',
        language: this.language || 'sql',
        readOnly: this.readOnly,
        automaticLayout: true,
        minimap: { enabled: false },
        lineNumbers: 'on',
        scrollBeyondLastLine: false,
        fontSize: 12,
        fontFamily: "'Roboto', sans-serif",
        theme: 'vs',
        lineDecorationsWidth: 4,
        glyphMargin: false,
        folding: true,
        renderLineHighlight: 'all',
        overviewRulerBorder: false,
        hideCursorInOverviewRuler: true
      });

      this.monacoEditorInstance.onDidChangeModelContent(() => {
        const val = this.monacoEditorInstance.getValue();
        this.code = val;
        this.codeChange.emit(val);
      });

      this.isMonacoActive.set(true);
    } catch (e) {
      this.isMonacoActive.set(false);
    }
  }
}
