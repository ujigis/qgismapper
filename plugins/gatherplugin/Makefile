
UIC=pyuic4
RCC=pyrcc4
UI_SOURCES=$(wildcard *.ui SourcePlugins/*.ui)
UI_FILES=$(patsubst %.ui,%_ui.py,$(UI_SOURCES))

all: resources.py ${UI_FILES}

resources.py: resources.qrc
	${RCC} -o resources.py resources.qrc

$(UI_FILES): %_ui.py: %.ui
	${UIC} $< > $@

clean:
	rm -f *.pyc SourcePlugins/*.pyc
	rm -f ${UI_FILES}
