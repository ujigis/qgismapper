
UIC=pyuic4
RCC=pyrcc4
UI_SOURCES=$(wildcard *.ui SourcePlugins/*.ui)
UI_FILES=$(patsubst %.ui,%_ui.py,$(UI_SOURCES))

all: resources_rc.py ${UI_FILES}

resources_rc.py: resources.qrc
	${RCC} -o resources_rc.py resources.qrc

$(UI_FILES): %_ui.py: %.ui
	${UIC} $< > $@

clean:
	rm -f *.pyc SourcePlugins/*.pyc
	rm -f ${UI_FILES}
